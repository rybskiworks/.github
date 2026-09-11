# Rybskiworks governance, CI and release plan

Status: reviewed implementation plan and staged foundation. September 11, 2026.
Definitions and workflow code are not evidence that GitHub settings are active.
The owner reviews and merges every implementation PR. This rollout never merges
PRs, rewrites existing history, changes default branches, or publishes a release
as a side effect of installing policy infrastructure.

## 1. Decisions and boundaries

Treat repositories by purpose, not GitHub's `fork` boolean. Detached derivatives
remain derived repositories. Preserve their upstream attribution, licensing and
merge ancestry. First-party projects own their own compatibility contract.

The initial critical set is `.github`, `nix-tooling`, and `workestrate`.
Workestrate's engineering base is `migration/tool-model`; its legacy default
`main` is not the source of truth for runtime design or CI assessment. The edge
already consumes a pinned nix-tooling revision and follows its shared inputs.
Preserve that architecture and all current dependency pins during installation.

Separate four things which are often mistakenly treated as one:

1. Integrity: who can destroy or rewrite a durable ref.
2. Integration authority: who can update the integration branch through a merge.
3. Admission checks: which evidence must exist before that update.
4. Credential custody: which processes can obtain privileged tokens.

A PR requirement with zero approvals provides a review surface, not exclusive
human merge authority. An agent with repository write access is not prevented
from merging merely because it works on `agents/**`. Likewise, a required status
from GitHub Actions is not proof that an agent could not modify the workflow
which emitted it. Initially, a human merger reviews both code and gate changes.
Trusted-policy execution is a prerequisite for future unattended merging.

## 2. Repository classification

Maintain an audited registry with these conceptual properties:

| Property | Values |
| --- | --- |
| repo_role | first_party, fork_derived, config_state, meta, scratch |
| criticality | critical, standard, experimental |
| release_model | semver, downstream, none |
| ci_profile | rust_nix, nix, upstream, config, none |
| automation_managed | explicit opt-in |
| integration_branch | explicit override or default branch |

Initially `.github` is critical meta infrastructure; nix-tooling is critical
first-party Nix infrastructure; Workestrate is critical first-party Rust/Nix
infrastructure with the explicit integration-branch override above. Custom
properties are an optional GitHub-admin projection of this registry, not a
prerequisite for using the first static rulesets. Do not infer entitlement from
repository visibility or a user's admin flag. Check organization plan, Actions
permissions, environments, rulesets and installed App scopes first.

The public `.github` repository must not become an inventory of private fleets,
internal upstreams, credentials, employer code, or private downstream test logs.
Keep private mappings in a private coordinator and publish only sanitized
contracts and results.

## 3. Additive rule layers

### 3.1 Immediately eligible integrity definitions

`rulesets/safe/` contains exactly three independently named policies:

| Definition | Target | Enforcement |
| --- | --- | --- |
| rw-default-integrity-v1 | all repositories, ~DEFAULT_BRANCH | no deletion; no non-fast-forward updates |
| rw-upstream-integrity-v1 | all repositories, upstream/* and upstream/**/* | no deletion; no non-fast-forward updates |
| rw-workestrate-edge-integrity-v1 | Workestrate, migration/tool-model only | no deletion; no non-fast-forward updates |

These layers have no bypass actors. A sync bot must not gain deletion/rewrite
permission just because it needs ordinary fast-forward updates. They add no CI
requirement, review requirement, signed-commit requirement, or rename policy.
GitHub may also block a default-branch change/rename when force-push protection
has no bypass, so a future default-branch migration needs its own reviewed
administrative procedure. No such transition is included here.

Do not automatically protect every `migration/**` or `sync/**` branch. Durable
tracking and integration refs are different from disposable work branches.
Legacy names such as `prime-upstream-sync` need individual classification; do
not silently rename, delete, or assume they are permanent mirrors.

### 3.2 PR and integration authority, staged together

The staged first-party PR layer requires PRs, zero approvals, and resolved
review threads. The owner may bypass this layer only through a PR. The separate
update-authority layer allows organization administrators to update integration
refs. Its `always` bypass is limited to that one authority rule; it does not
bypass the separate integrity or PR layers. Use a named human maintainer team
instead once its actual membership and identifier have been audited.

Apply both layers to critical default branches and an explicit Workestrate edge
rule. Agents and general automation do not receive integration-authority bypass.
Confirm that the agents are not organization administrators and do not possess
owner credentials. Without this identity audit, the label "human-only" would
be misleading.

Review state/config and mirror repositories before expanding PR requirements.
Some may legitimately have append-only machine writers. Never solve their
workflow by giving a general bot bypass over every rule. New requirements must
not overwrite, disable, or broaden the bypass lists of existing rulesets.

### 3.3 Required evidence

After the workflow PR has merged and real checks have completed, add a separate
required-check layer. Select the exact observed check context and emitting App,
not a guessed workflow filename. Workestrate will retain its historical
`required-gates (branch-protection anchor)` while adding `CI / required`.
Nix-tooling uses its own `CI / required`; governance uses `Governance / required`.
The meanings of these checks differ and are documented below.

Start with loose up-to-date checking. Do not introduce merge queues, enforced
linear history, squash-only repository settings, or a global signed-commit
requirement during migration. Preserve real merge commits for upstream imports
and eventual migration promotion. Prefer conventional squash titles for ordinary
first-party feature PRs without rewriting imported history.

### 3.4 Release tags

For first-party SemVer repositories, stage a no-update/no-delete policy for
`refs/tags/v*`. Validate full SemVer in the publisher because `v*` is deliberately
broader than a SemVer regular expression. A separate creation-authority policy
will allow the dedicated release App to create tags after its real App ID and
permissions are known. That App gets no bypass on tag integrity or integration
branch checks. Imported upstream tags and downstream fork release names require
separate explicit namespaces; do not capture every fork's tags with this policy.

## 4. Administration workflow and rollback

The supplied Python tool uses the operator's authenticated `gh` session. It
cannot use a content-only GitHub connection to create administrative settings.
No administration secret is stored in Git or supplied to Actions.

```sh
python3 scripts/rulesets.py --validate-only
python3 scripts/rulesets.py --scope orgs/rybskiworks
```

Review the emitted snapshot and create-only plan. Then, using its exact digest:

```sh
python3 scripts/rulesets.py --scope orgs/rybskiworks \
  --apply --expected-plan-sha256 DIGEST_FROM_REVIEWED_PLAN \
  --receipt /secure/new-ruleset-receipt.json
```

The receipt must not already exist. The tool creates only safe integrity
rulesets, checks current state before every write, verifies the result, and
records every created ID in a private receipt. A matching managed rule is a
no-op; a conflicting rule with the same name is an error. Incomplete visibility,
including missing bypass information, aborts. POST failures are not retried
because the server might already have committed the request. Partial completion
is recorded, not rolled back by deleting rules. Reinspect before rerunning.

If org rules are unavailable but a repository is entitled, use an explicit
`--scope repos/rybskiworks/REPOSITORY`. This is a deliberate per-repository
fallback, not automatic scope expansion. It preserves inherited org rules and
does not apply Workestrate's branch exception elsewhere. Evaluate mode is not a
portable prerequisite: GitHub documents it as Enterprise-only. Read-only planning
and a small active canary are the non-Enterprise alternative.

This tool intentionally cannot install `rulesets/staged/`, change settings,
create identities, change plans, or remove rules. Any later administrative
relaxation is a separate, human-reviewed operation with the original receipt.

## 5. What belongs in .github

Use three distinct mechanisms:

- Root contribution/security/issue/PR defaults: fallbacks for repositories which
  do not supply their own supported community-health files.
- `workflow-templates/`: starter callers, not automatically installed workflows.
- `.github/workflows/reusable-*.yml`: explicitly called versioned implementation.

CODEOWNERS and Dependabot require repository-local files. Existing upstream
policies and licenses take precedence in derived repositories. Keep `.github`
critical because modifying shared automation can affect every consumer.

Pin Actions and reusable workflows to reviewed full commit SHAs. Pin downloaded
tool/compiler versions separately. A pinned installer is not a pinned compiler.
Use Dependabot for Actions; retain Workestrate's deliberate exclusion of Cargo
updates that would fight its managed fork lock. Record the automation revision
in rollout receipts. Replace template placeholders before installation; after
the governance PR is reviewed, use its exact approved commit in callers.

The initial reusable primitives implement read-only PR-title validation, a pinned
Nix evaluation/full-check tier, metadata-only draft PR creation, and release-PR
preparation without tagging or publication. Write-capable jobs never check out
or execute a PR's code. The optional release token is a short-lived, repository-
scoped token, not an App private key. Feature switches are off until protections,
workflow creation policy and token behavior have been tested.

## 6. Workestrate CI and version authority

Build on `migration/tool-model`, not legacy main. Preserve the existing cheap
Rust/pin checks, explicit Nix/msb/agentd provisioning, manual heavy build, and the
resource constraints which motivated avoiding a full devenv closure on each PR.

The revised workflow starts on every PR. Path classification occurs inside the
workflow; unknown, empty, or unavailable diffs select code checks. Ordinary
`docs/` changes can omit compilation, but workflow/security/metadata checks
still execute. Migration documentation remains code-relevant. A selected Nix
label must produce actual Nix evidence; unexpected skips, missing jobs, failures
and cancellations block the aggregate gate. Removing a label triggers fresh
classification; the release gate will not depend on a removable label.

The old anchor covered only the Rust `gates` job and could not run when the
entire workflow was path-filtered. It now aggregates policy, actionlint, zizmor,
license/source checks and all selected expensive tiers. The old actionlint
wrapper defaulted to non-failing reports; invoke actionlint directly. Pin both
the Rust Action commit and the exact compiler patch version. Preserve the
existing informational advisory policy, explicitly distinguished from enforced
license/bans/source checks.

`control/agentctl/Cargo.toml` is Workestrate's version authority. The Nix package
reads `manifest.package.version`; a metadata guard checks the local Cargo.lock
entry agrees. Leave the source version and dependency pins unchanged in this
foundation. A successful package build with `doCheck = false` is not a test
result. Ignored KVM tests and runtime tests skipped for unavailable prerequisites
remain missing evidence, never release-qualified green checks.

## 7. Nix-tooling CI and compatibility

Treat nix-tooling as a curated toolchain and module compatibility boundary, not
just a convenient nixpkgs alias. Retain its owned Fenix revision and the
consumer's existing `follows` graph. Its initial supported target remains
x86_64-linux. Do not add unsupported platforms to create an impressive matrix.

The initial CI runs inexpensive metadata/workflow checks and Nix evaluation.
A selected `nix-ci` label or manual dispatch executes full flake checks with
explicit resource limits. All selected checks participate in the final gate.
Evaluation is not a compiled package, guest boot, or downstream compatibility
claim. Do not require this new check administratively until its first genuine
runs reveal resource and environment requirements.

Add `version.txt` as the tooling contract version, explicitly unpublished until
a real release exists. Define SemVer over documented exported attributes,
module options/defaults, configuration behavior, supported tools and observable
runtime contracts. Routine pin updates are not automatically safe patches;
classify their actual compatibility impact. Never automatically bump a
consumer's NixOS `stateVersion` as a dependency-maintenance task.

Run private Workestrate compatibility tests inside Workestrate or an isolated
private coordinator, checking out exact candidate/tooling and consumer SHAs.
Do not hand a public nix-tooling PR a token that can read Workestrate. Return a
sanitized attested result or owner-reviewed receipt, not private source/logs.
Select downstream consumers from a private registry. Missing downstream runs
must block promotion rather than be treated as success.

## 8. Releases and promotion

Keep preparation, verification and publication separate. Release Please is an
available PR-preparation primitive, not an automatically authorized publisher.
Its consumer config and initial baseline need their own validated bootstrap.
Inventory existing tags as well as releases before choosing the first tag.
Absence of a GitHub Release does not prove that no tag exists.

Nix-tooling can use a root simple/version.txt strategy. Workestrate needs
repository-wide change accounting: naively setting a Rust release path to
`control/agentctl` would miss Nix/config-only changes. Validate the chosen root
strategy and transactional Cargo.toml/Cargo.lock/changelog updates with fixtures
before enabling it. Do not add an independently drifting version file to avoid
solving this. Initial conventions are fixes -> patch, compatible features ->
minor, and breaking changes -> explicitly documented minor while 0.x. Reaching
1.0 is a conscious compatibility declaration; breaking changes become major.

Build release infrastructure against the edge branch. Before migration
promotion, choose an explicit prerelease channel such as `v0.1.0-rc.1` if
artifacts are needed. Do not equate a migration branch with a stable release.
The final publication pipeline must:

1. Identify a human-merged release PR and its exact authorized commit. Verify
   branch, version, tag absence/identity, all required same-SHA CI evidence and
   the compatible nix-tooling revision. Serialize publication per repository.
2. Build/test in a secretless isolated job. Record source, locks, compiler,
   builder, workflow revision, checksums and the exact tests which ran. Full
   runtime/KVM acceptance belongs here once supported, not behind an optional
   PR label. Never rebuild different source under an already approved version.
3. Use a separate narrow publisher to create a draft release at the verified
   SHA, attach verified artifacts and a machine-readable release manifest, then
   publish. Validate filenames, digests, sizes and expected inventory; do not
   execute artifacts in the privileged publisher.
4. Enable immutable releases after entitlement/settings verification. Tags and
   assets are locked on publication; titles and release notes remain editable.
   Include relevant metadata in an attached immutable manifest. GitHub release
   attestations and build attestations are distinct; add the latter/SBOM where
   supported without pretending unsupported private-plan features are active.
5. On rerun, verify an existing matching draft/tag rather than force replacing
   it. A mismatching tag/artifact or ambiguous prior publication stops the run.
   Never delete a published release or retag to make a retry succeed.

A published tooling release should propose a Workestrate dependency PR against
`migration/tool-model` until promotion. Resolve the immutable tag to a full
revision; retain the follows graph; update only the intended input/lock subgraph.
Record old/new source versions and revisions and run downstream tests. Raw SHA
pins remain valid and may be retained with release metadata; switching to a tag
is not inherently a security improvement. Do not silently absorb tooling main.

## 9. Fork and agent automation

An upstream mapping contains explicit upstream repository/ref, permanent
tracking ref, integration target, permitted actor, check profile and merge
method. This works for ordinary forks, detached forks and multiple meaningful
ancestors. Never choose GitHub's original source instead of an intended
intermediate parent merely because metadata suggests it.

The future importer fetches in an isolated unprivileged process, verifies the
configured source, and fast-forwards `upstream/<owner>/<branch>` without running
upstream workflows. Preserve commit identities and ancestry. Non-fast-forward
upstream changes stop; keep the old ref and require a reviewed recovery/new
namespace. Do not automatically reset a permanent mirror to "fix" divergence.

The delivered PR primitive can propose an existing permanent tracking ref into
its configured target. It creates at most one draft PR, treats no new commits as
a no-op, and respects human closure. A closed-unmerged tracking pair suppresses
future automatic proposals until an operator deliberately changes that policy.
Conflict resolution occurs in a disposable `sync/upstream/...` branch and is
reviewed; imports merge with real merge commits. External contribution PRs are
separately authorized, not an automatic consequence of local synchronization.

Agent pushes can use the same draft-PR primitive for `agents/**`. A new task uses
a new branch; a merged agent branch is not reused to silently create more work.
The configured integration base is explicit for Workestrate. PR metadata is
never interpolated as executable shell. Labels and branch names provide routing,
not authentication, merge permission or proof of author identity.

GitHub's current GITHUB_TOKEN behavior can leave automatically created PR runs
awaiting human approval. That is the safe initial mode. Unattended events require
a separate scoped App token supplied by a trusted coordinator. Do not install a
multi-repository App private key into a repository where agents can edit and run
workflows. Branch protection alone does not secure repository secrets.

Automatic deletion of disposable branches remains off until permanent-ref
protection is tested. No branches are deleted in this rollout. Later enable
cleanup selectively, excluding persistent tracking/integration/release support
branches. No auto-merge, auto-approval, or automatic conflict resolution is part
of the foundation.

## 10. Acceptance and rollout order

| Stage | Deliverable | Acceptance before advancement |
| --- | --- | --- |
| 0 | Inventory and authorization | full admin visibility, plan/entitlement and actor audit |
| 1 | Additive integrity policies | exact targets, no bypasses, deny-delete/deny-rewrite canary tests |
| 2 | .github foundation PR | Python policy tests, actual PR-script tests, workflow lint, owner review |
| 3 | Workestrate edge CI PR | old anchor preserved, selected jobs fail closed, actual Actions evidence |
| 4 | nix-tooling CI/version PR | pure metadata checks plus real evaluation; full-check resource measurements |
| 5 | Required CI + human merge authority | observed App/check context, same identity cannot bypass another layer |
| 6 | Repo-local callers/default bootstrap | reviewed full workflow SHA; feature flags initially off |
| 7 | Trusted sync and release coordinator | scoped tokens, no code execution with publisher/admin credentials |
| 8 | Prerelease and downstream promotion | exact-SHA build/runtime evidence, immutable complete artifacts |
| 9 | Limited autonomous lanes | owner opt-in, proven trusted gates, no conflict/breaking-change autopilot |

For canary validation, test allowed agent branch pushes and denied integration
updates using the actual machine identity. Test denied deletion/force-push on
both shallow and nested upstream names, and retained freedom on disposable sync
branches. Test a human PR merge, failed/cancelled/missing selected CI, duplicate
PR events, upstream rewrites, App revocation and partial publication failures.
Do destructive tests only on dedicated canary refs, never production branches.

A read-only drift auditor should compare observed settings to approved receipts,
report missing protection and stalled sync/release PRs, and deduplicate alerts.
It must not repair drift by changing or removing protection without review.
Default-branch-only event registration (Dependabot, schedules and dispatch) needs
an explicit bootstrap when engineering lives on a non-default branch. A small
metadata-only PR to Workestrate main can install its Dependabot config with
`target-branch: migration/tool-model`; it must not copy legacy runtime code into
the edge or promote the migration accidentally.

## 11. Implementation status of this foundation

This foundation supplies additive integrity definitions and a create-only
operator tool, staged authority/PR/tag definitions, community defaults,
workflow templates, and reusable Nix/title/draft-PR/release-PR primitives.
Companion PRs harden Workestrate's edge CI and introduce nix-tooling CI/version
metadata. None of these files alone activates repository protections.

The upstream fetch/import coordinator, private downstream compatibility
reporter, transactional Workestrate release calculator, build/publish pipeline,
immutable-release settings, full KVM release gates, and selective auto-merge
remain separately gated implementation milestones. They are not represented as
already running. An inaccessible admin API is not a reason to put a broad admin
credential in an agent-controlled Actions job.

## References

- [Rules and merge/update authority](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets)
- [Organization rules API, permissions and evaluation entitlement](https://docs.github.com/en/rest/orgs/rules)
- [Ruleset creation, targeting and bypasses](https://docs.github.com/en/organizations/managing-organization-settings/creating-rulesets-for-repositories-in-your-organization)
- [Required-check troubleshooting and skipped workflows](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/troubleshooting-required-status-checks)
- [Reusable workflows and immutable references](https://docs.github.com/en/actions/how-tos/reuse-automations/reuse-workflows)
- [Organization workflow templates](https://docs.github.com/en/actions/how-tos/reuse-automations/create-workflow-templates)
- [Community-health defaults](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/creating-a-default-community-health-file)
- [GITHUB_TOKEN and approval-required PR workflows](https://docs.github.com/en/actions/concepts/security/github_token)
- [Actions security hardening](https://docs.github.com/en/actions/reference/security/secure-use)
- [Workflow events and default-branch constraints](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)
- [Dependabot target-branch configuration](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference)
- [Release Please Action](https://github.com/googleapis/release-please-action)
- [Release Please manifest options](https://github.com/googleapis/release-please/blob/main/docs/manifest-releaser.md)
- [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
- [Immutable releases](https://docs.github.com/en/code-security/concepts/supply-chain-security/immutable-releases)
- [Build attestations](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations)
