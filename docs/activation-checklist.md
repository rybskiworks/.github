# Activation checklist

This supplements the governance plan. Code review and an approved commit do not by themselves establish live enforcement.

## Preserve the shared implementation revision

The starter callers and companion PRs pin `3a7ef7dd7d23aedba866cb3a3a5df26ff2f86a7c`, the first implementation commit of the governance foundation. Prefer a merge commit for this initial governance PR so that exact implementation remains in main's ancestry. If squashing or rebasing, re-pin dependent callers to the resulting reviewed main commit before activation. Do not replace a full SHA with moving `main` merely to make adoption easier.

## Observe checks on the exact intended branch

Workestrate's full engineering/CI change targets `migration/tool-model`. Its main bootstrap only adds Dependabot configuration. Do not require the edge's CI contexts on legacy main until a corresponding workflow actually exists and has completed there. Observe actual emitted check names and App identity rather than inferring them from filenames or display labels. A successful evaluation-only nix-tooling run is not a release-qualified build.

## Upstream pushes can trigger imported workflows

Fetching Git objects without executing their contents is only half the boundary. A GitHub App-token push may also trigger workflows stored in the imported tree. Do not activate a generic App-powered fast-forward importer on the assumption that updating a tracking ref cannot execute upstream automation.

Before deployment, demonstrate the selected ingestion path suppresses or isolates those events. A repository GITHUB_TOKEN suppresses ordinary push-triggered workflows, but allowing the generic GitHub Actions identity to update protected tracking refs has separate authorization implications, especially with same-repository agent writers. An Actions-disabled staging/mirror design is another candidate, with promotion and fork-network constraints to validate. Do not grant a general Actions identity broad bypass or edit imported history to hide this problem. Until ingestion and publication identity boundaries pass canary tests, keep the importer disabled and use the delivered metadata-only PR primitive only on deliberately prepared refs.

## Token custody and release activation

No organization-admin token belongs in Actions. No multi-repository App key belongs in an agent-writable workflow repository. Keep private downstream checkout and logs out of public Nix PR jobs. The release-PR helper's optional token is repository-scoped and short-lived; it is not a place to upload an App key.

Inventory existing tags, validate the initial release baseline, test repo-wide change accounting, configure publisher identity and immutable-release settings, and obtain exact-SHA full build/test evidence before enabling publication. Preserve existing dependency pins until a verified upgrade PR is accepted. Existing draft/tag mismatches stop publication; they do not authorize delete-and-retry.

## Prove policies with real identities

Use dedicated canary refs to test allowed agent topic pushes, denied agent integration updates, allowed human PR merges, denied shallow/nested upstream deletion and force-push, and expected disposable-branch behavior. Confirm no machine identity holds an administrative role. Only after required checks exist and these identity tests pass should agent PR feature switches be enabled. Unattended merging remains a separate opt-in milestone.

References: [GITHUB_TOKEN event behavior](https://docs.github.com/en/actions/concepts/security/github_token), [workflow events](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows), [available rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets), [immutable releases](https://docs.github.com/en/code-security/concepts/supply-chain-security/immutable-releases).
