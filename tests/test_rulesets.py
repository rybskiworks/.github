import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('rulesets', ROOT / 'scripts/rulesets.py')
rules = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rules)

class FakeGitHub:
    def __init__(self):
        self.rows = []
        self.calls = []
    def api(self, method, path, data=None, pages=False):
        self.calls.append((method, path))
        if method == 'GET' and pages:
            # More than one page, including an empty page, is intentionally covered.
            return [copy.deepcopy(self.rows[:1]), copy.deepcopy(self.rows[1:])]
        if method == 'GET':
            return copy.deepcopy(next(x for x in self.rows if str(x['id']) == path.rsplit('/', 1)[-1]))
        if method == 'POST' and path == 'orgs/rybskiworks/rulesets':
            row = dict(copy.deepcopy(data), id=100 + len(self.rows), source='rybskiworks', source_type='Organization')
            self.rows.append(row)
            return copy.deepcopy(row)
        raise AssertionError((method, path))

class RulesetTests(unittest.TestCase):
    def setUp(self):
        self.desired = rules.definitions('orgs/rybskiworks')
    def test_validate_definitions(self):
        self.assertEqual(len(self.desired), 3)
        for rule in self.desired:
            rules.validate_safe(rule)
    def test_reject_weaker_or_unexpected_rule(self):
        for field, value in [('bypass_actors', [{'actor_type': 'OrganizationAdmin'}]),
                             ('enforcement', 'disabled'), ('rules', [{'type': 'pull_request'}])]:
            candidate = copy.deepcopy(self.desired[0]); candidate[field] = value
            with self.assertRaises(ValueError): rules.validate_safe(candidate)
    def test_incomplete_visibility_is_not_empty_bypass(self):
        candidate = copy.deepcopy(self.desired[0]); del candidate['bypass_actors']
        with self.assertRaises(ValueError): rules.semantic(candidate)
    def test_scoped_fallback_does_not_broaden_migration_target(self):
        local = rules.definitions('repos/rybskiworks/nix-tooling')
        self.assertEqual(len(local), 2)
        self.assertTrue(all('repository_name' not in r['conditions'] for r in local))
        self.assertEqual(len(rules.definitions('repos/rybskiworks/workestrate')), 3)
    def test_scope_restriction(self):
        for scope in ['orgs/other', 'repos/other/repo', 'repos/rybskiworks/a/../../b']:
            with self.assertRaises(ValueError): rules.definitions(scope)
    def test_create_verify_and_idempotency(self):
        api = FakeGitHub()
        plan = rules.build_plan('orgs/rybskiworks', self.desired, rules.snapshot(api, 'orgs/rybskiworks'))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'receipt.json'
            result = rules.apply_plan(api, plan, plan['plan_sha256'], path)
            self.assertEqual(result['status'], 'verified')
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        after = rules.build_plan('orgs/rybskiworks', self.desired, rules.snapshot(api, 'orgs/rybskiworks'))
        self.assertEqual(after['create'], [])
        self.assertEqual(sum(m == 'POST' for m, _ in api.calls), 3)
        self.assertTrue(all(m in {'GET', 'POST'} for m, _ in api.calls))
    def test_mismatching_live_name_aborts(self):
        row = dict(copy.deepcopy(self.desired[0]), id=5, source='rybskiworks', source_type='Organization')
        row['enforcement'] = 'disabled'
        with self.assertRaises(ValueError): rules.build_plan('orgs/rybskiworks', self.desired, [row])
    def test_wrong_digest_never_writes(self):
        api = FakeGitHub(); plan = rules.build_plan('orgs/rybskiworks', self.desired, [])
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError): rules.apply_plan(api, plan, 'wrong', Path(tmp) / 'receipt.json')
        self.assertEqual(api.calls, [])
    def test_concurrent_change_stops_before_first_write(self):
        api = FakeGitHub(); plan = rules.build_plan('orgs/rybskiworks', self.desired, [])
        row = dict(copy.deepcopy(self.desired[0]), id=1, source='rybskiworks', source_type='Organization')
        row['name'] = 'unrelated'; api.rows = [row]
        with tempfile.TemporaryDirectory() as tmp:
            receipt = Path(tmp) / 'receipt.json'
            with self.assertRaises(RuntimeError): rules.apply_plan(api, plan, plan['plan_sha256'], receipt)
            self.assertEqual(json.loads(receipt.read_text())['status'], 'stopped')
        self.assertFalse(any(m == 'POST' for m, _ in api.calls))
    def test_receipt_never_overwritten(self):
        api = FakeGitHub(); plan = rules.build_plan('orgs/rybskiworks', self.desired, [])
        with tempfile.TemporaryDirectory() as tmp:
            receipt = Path(tmp) / 'receipt.json'; receipt.write_text('keep')
            with self.assertRaises(FileExistsError): rules.apply_plan(api, plan, plan['plan_sha256'], receipt)
            self.assertEqual(receipt.read_text(), 'keep')

if __name__ == '__main__': unittest.main()
