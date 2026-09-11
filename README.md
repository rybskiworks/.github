# Rybskiworks organization infrastructure

Shared contribution defaults, reviewed workflow primitives and additive policy definitions. The organization profile in `profile/` is independent and remains unchanged.

Start with [the governance and rollout plan](docs/governance.md). Definitions in Git are not live GitHub settings. No rule, custom property, secret, environment or permission is installed merely by merging this repository.

```sh
python3 -m unittest discover -s tests -v
python3 scripts/rulesets.py --validate-only
python3 scripts/rulesets.py --scope orgs/rybskiworks
```

The final command is read-only and needs `gh` authenticated with appropriate administration visibility. The create-only apply command is documented in the plan. No CI workflow has organization-administration credentials.

Workflow templates contain a clearly named commit placeholder and must be rendered before use. Reusable workflows must be called at a reviewed full commit SHA, not a moving branch. Existing repository overrides, licenses, CODEOWNERS and workflows are not replaced by these defaults.
