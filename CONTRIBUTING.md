# Contributing

Repository-specific instructions take precedence over these defaults. For a derived repository, preserve upstream attribution, licensing, contribution requirements and merge ancestry.

Use a topic branch and a pull request. Describe the change, the evidence that it works, its compatibility impact and how to revert it. List skipped or unavailable checks explicitly. A successful build is not proof that runtime or isolation tests passed.

For first-party projects, prefer Conventional Commit PR titles, for example `fix(runtime): preserve isolation on reconnect`. Mark breaking changes with `!` and explain the migration. Do not rewrite imported upstream commit messages to satisfy a local convention.

Agents use their own identities and permitted branch namespaces. A branch name, author field, label, or passing check is not authorization to merge, release, retrieve credentials, or broaden network access. Do not put credentials in branches, PRs, logs or artifacts.

Keep changes focused. Policy and workflow changes require the same review as application code. Do not merge your own automation PR merely because CI is green. See [the governance plan](docs/governance.md).
