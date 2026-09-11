#!/usr/bin/env python3
"""Plan or create additive integrity rules. Never update/delete existing rules.

Only definitions in rulesets/safe are eligible. Uses the operator's gh session;
no administration credential belongs in repository Actions. Python 3.11+.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
KEYS = ('name', 'target', 'enforcement', 'bypass_actors', 'conditions', 'rules')


def digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(',', ':')).encode()
    return hashlib.sha256(raw).hexdigest()


def semantic(rule: dict[str, Any]) -> dict[str, Any]:
    # An omitted bypass list can mean insufficient access, NOT no bypass actors.
    if any(k not in rule for k in KEYS):
        raise ValueError('Incomplete ruleset visibility; refusing to infer missing fields')
    return {k: rule[k] for k in KEYS}


def validate_safe(rule: dict[str, Any]) -> None:
    semantic(rule)
    if set(rule) != set(KEYS):
        raise ValueError('Unknown ruleset fields')
    if not re.fullmatch(r'rw-[a-z0-9-]+-v[0-9]+', rule['name']):
        raise ValueError('Invalid managed name')
    if rule['target'] != 'branch' or rule['enforcement'] != 'active' or rule['bypass_actors']:
        raise ValueError('Safe definitions must be active branch integrity rules without bypasses')
    if sorted(rule['rules'], key=lambda x: x['type']) != [{'type': 'deletion'}, {'type': 'non_fast_forward'}]:
        raise ValueError('Only deletion and force-push prevention are allowed in safe apply')
    conditions = rule['conditions']
    if set(conditions) != {'repository_name', 'ref_name'}:
        raise ValueError('Unsupported condition type')
    selector = conditions['repository_name']
    if selector.get('exclude') != [] or selector.get('protected') is not False:
        raise ValueError('Do not alter repository renaming or silently exclude repositories')
    if selector.get('include') not in (['~ALL'], ['workestrate']):
        raise ValueError('Unexpected repository selector')
    refs = conditions['ref_name']
    allowed = [
        ['~DEFAULT_BRANCH'],
        ['refs/heads/upstream/*', 'refs/heads/upstream/**/*'],
        ['refs/heads/migration/tool-model'],
    ]
    if set(refs) != {'include', 'exclude'} or refs['exclude'] or refs['include'] not in allowed:
        raise ValueError('Unexpected branch selector')
    if refs['include'] == ['refs/heads/migration/tool-model'] and selector['include'] != ['workestrate']:
        raise ValueError('Migration branch must be scoped to Workestrate')


def definitions(scope: str) -> list[dict[str, Any]]:
    if not re.fullmatch(r'(orgs/rybskiworks|repos/rybskiworks/[A-Za-z0-9_.-]+)', scope):
        raise ValueError('Scope must be the rybskiworks org or one of its repositories')
    files = sorted((ROOT / 'rulesets' / 'safe').glob('*.json'))
    if not files:
        raise ValueError('No safe definitions found')
    result = []
    for path in files:
        rule = json.loads(path.read_text())
        validate_safe(rule)
        rule = copy.deepcopy(rule)
        if scope.startswith('repos/'):
            repositories = rule['conditions'].pop('repository_name')['include']
            if '~ALL' not in repositories and scope.rsplit('/', 1)[-1] not in repositories:
                continue
        result.append(rule)
    if len({r['name'] for r in result}) != len(result):
        raise ValueError('Duplicate desired names')
    return result


class GitHub:
    def api(self, method: str, path: str, data: Any = None, pages: bool = False) -> Any:
        if method not in {'GET', 'POST'} or (method == 'POST' and not path.endswith('/rulesets')):
            raise ValueError('Only GET and create-ruleset POST are supported')
        args = ['gh', 'api', '--hostname', 'github.com', '--method', method,
                '-H', 'Accept: application/vnd.github+json',
                '-H', 'X-GitHub-Api-Version: 2026-03-10', path]
        if pages:
            args.extend(['--paginate', '--slurp'])
        if data is not None:
            args.extend(['--input', '-'])
        process = subprocess.run(args, input=json.dumps(data) if data is not None else None,
                                 text=True, capture_output=True, check=False)
        if process.returncode:
            raise RuntimeError(f'GitHub {method} failed ({process.returncode}); no fallback or retry. '
                               + process.stderr.strip())
        return json.loads(process.stdout)


def snapshot(client: GitHub, scope: str) -> list[dict[str, Any]]:
    query = f'{scope}/rulesets?per_page=100'
    if scope.startswith('repos/'):
        query += '&includes_parents=true'
    pages = client.api('GET', query, pages=True)
    if not isinstance(pages, list) or any(not isinstance(page, list) for page in pages):
        raise ValueError('Unexpected paginated ruleset response')
    rows = []
    seen = set()
    for page in pages:
        for entry in page:
            kind, source, identity = entry.get('source_type'), entry.get('source'), entry.get('id')
            if kind not in {'Organization', 'Repository'} or not isinstance(identity, int):
                raise ValueError('Unsupported inherited source; obtain a complete administration snapshot')
            if not isinstance(source, str) or not re.fullmatch(r'[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)?', source):
                raise ValueError('Invalid ruleset source')
            key = (kind, source, identity)
            if key in seen:
                raise ValueError('Duplicate ruleset in paginated response')
            seen.add(key)
            prefix = 'orgs' if kind == 'Organization' else 'repos'
            detail = client.api('GET', f'{prefix}/{source}/rulesets/{identity}')
            rows.append({'id': identity, 'source_type': kind, 'source': source, **semantic(detail)})
    return sorted(rows, key=lambda x: (x['source_type'], x['source'], x['id']))


def build_plan(scope: str, desired: list[dict[str, Any]], current: list[dict[str, Any]]) -> dict[str, Any]:
    creates, already = [], []
    owner = scope.split('/', 1)[1]
    kind = 'Organization' if scope.startswith('orgs/') else 'Repository'
    for wanted in desired:
        named = [r for r in current if r['name'] == wanted['name'] and
                 r['source'] == owner and r['source_type'] == kind]
        if len(named) > 1:
            raise ValueError(f"Duplicate live managed name: {wanted['name']}")
        if named:
            if semantic(named[0]) != wanted:
                raise ValueError(f"Existing rule differs: {wanted['name']}; no overwrite permitted")
            already.append({'name': wanted['name'], 'id': named[0]['id']})
        else:
            creates.append(wanted)
    plan = {'scope': scope, 'before': current, 'create': creates, 'unchanged_managed': already}
    return {**plan, 'plan_sha256': digest(plan)}


def receipt_write(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2) + '\n')


def apply_plan(client: GitHub, plan: dict[str, Any], expected: str, receipt: Path) -> dict[str, Any]:
    if expected != plan['plan_sha256']:
        raise ValueError('Plan changed or incorrect plan digest; run the read-only plan again')
    # Exclusive private receipt: never overwrite an existing receipt or follow a pre-existing symlink.
    fd = os.open(receipt, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(fd)
    result = {'plan': plan, 'created': [], 'status': 'started',
              'started_at': datetime.now(timezone.utc).isoformat()}
    receipt_write(receipt, result)
    expected_state = plan['before']
    try:
        for wanted in plan['create']:
            latest = snapshot(client, plan['scope'])
            if latest != expected_state:
                raise RuntimeError('Live state changed; stop and replan. Prior creations remain recorded.')
            created = client.api('POST', f"{plan['scope']}/rulesets", wanted)
            if not isinstance(created.get('id'), int):
                raise RuntimeError('Create response has no id; inspect GitHub before retrying')
            result['created'].append({'id': created['id'], 'name': wanted['name']})
            receipt_write(receipt, result)
            after = snapshot(client, plan['scope'])
            added = [r for r in after if r not in expected_state]
            if any(r not in after for r in expected_state) or len(added) != 1 or semantic(added[0]) != wanted:
                raise RuntimeError('Post-create verification failed; no automatic rollback or retry')
            if added[0]['id'] != created['id']:
                raise RuntimeError('Created rule id mismatch')
            expected_state = after
        result['status'] = 'verified'
    except Exception as exc:
        result['status'] = 'stopped'
        result['error'] = str(exc)
        raise
    finally:
        receipt_write(receipt, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scope', default='orgs/rybskiworks')
    parser.add_argument('--validate-only', action='store_true')
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--expected-plan-sha256')
    parser.add_argument('--receipt', type=Path)
    args = parser.parse_args()
    if args.validate_only and args.apply:
        parser.error('--validate-only and --apply are mutually exclusive')
    desired = definitions(args.scope)
    if args.validate_only:
        print(json.dumps({'validated': [x['name'] for x in desired]}, indent=2))
        return
    client = GitHub()
    plan = build_plan(args.scope, desired, snapshot(client, args.scope))
    if args.apply:
        if not args.expected_plan_sha256 or args.receipt is None:
            parser.error('--apply requires --expected-plan-sha256 and a new --receipt path')
        result = apply_plan(client, plan, args.expected_plan_sha256, args.receipt)
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps(plan, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, RuntimeError, OSError, KeyError, TypeError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        raise SystemExit(1)
