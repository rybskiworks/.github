# Rybskiworks organization infrastructure

Shared contribution defaults, reviewed workflow primitives and additive policy definitions. The organization profile in `profile/` is independent and remains unchanged.

Start with [the governance and rollout plan](docs/governance.md). Definitions in Git are not live GitHub settings. No rule, custom property, secret, environment or permission is installed merely by merging this repository.

```sh
python3 -m unittest discover -s tests -v
node tests/test_open_pr.mjs
python3 scripts/rulesets.py --validate-only
python3 scripts/rulesets.py --scope orgs/rybskiworks
```

The final command is read-only and needs `gh` authenticated with appropriate administration visibility. The create-only apply command is documented in the plan. No CI workflow has organization-administration credentials.

Workflow templates pin the foundation implementation to a full commit SHA. Review that implementation before adopting a caller. GitHub replaces `$default-branch` when using a template; Workestrate callers deliberately use `migration/tool-model` instead. The upstream template also needs an explicit source/tracking mapping before enablement. Existing repository overrides, licenses, CODEOWNERS and workflows are not replaced by these defaults.

Release preparation and agent/upstream PR callers are opt-in. The repository contains no unattended publisher, upstream importer, or organization-administration workflow. See the plan's implementation-status section for gated follow-up milestones.
