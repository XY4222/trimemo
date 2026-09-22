# CLI Commands

All commands accept `--palace <path>` to override the default palace location.
The top-level command also accepts `--backend <name>` to select a storage
backend such as `sqlite_exact`, `milvus`, `qdrant`, or `pgvector`.

## `trimemo update`

Release checks are disabled by default. Enable weekly checks explicitly with
`trimemo update configure --enable --installer uv-tool` (using `pipx` or
`pip` when that is how the runtime was installed), or disable them with `--disable`.
`trimemo update check` performs an explicit check regardless of that setting.
`trimemo update plan` prints the runtime, skill, restart, and tool-refresh
actions but never executes them. Command actions use structured `argv`; for a
`pip` installation the first argument is the exact interpreter running
TriMemo, not whichever `python` happens to be on `PATH`. For an explicit check made without saved setup
state, pass the matching installer to `plan --installer`. Cached state appears in `mempalace_status` so
agents can ask the user to authorize an upgrade without blocking on a network
request.

## `trimemo init`

Scan a project directory for people, projects, and rooms, and set up the palace.

```bash
trimemo init <dir>                 # <dir> is required
trimemo init <dir> --yes           # non-interactive mode
trimemo init ~/projects/myapp      # example
trimemo init .                     # initialize from the current directory
```

| Option  | Description                                                                  |
|---------|------------------------------------------------------------------------------|
| `<dir>` | **Required.** Project directory to scan. Pass `.` for the current directory. |
| `--yes` | Auto-accept all detected entities                                            |

What it does:

1. Scans `<dir>` for people and projects in file content
2. Detects rooms from `<dir>`'s folder structure
3. Saves detected entities to `<dir>/entities.json`
4. Ensures the global `~/.mempalace/` config directory exists

Running `trimemo init` with no argument will exit with
`error: the following arguments are required: dir`.

## `trimemo mine`

Mine files into the palace.

```bash
trimemo mine <dir>
trimemo mine <dir> --mode convos
trimemo mine <dir> --mode convos --extract general
trimemo mine <dir> --wing myapp
```

| Option | Default | Description |
|--------|---------|-------------|
| `<dir>` | — | Directory to mine |
| `--mode` | `projects` | `projects` for code/docs, `convos` for chat exports |
| `--wing` | directory name | Wing name override |
| `--agent` | `trimemo` | Agent name tag |
| `--limit` | `0` (all) | Max files to process |
| `--dry-run` | — | Preview without filing |
| `--extract` | `exchange` | `exchange` or `general` (for convos mode) |
| `--no-gitignore` | — | Don't respect .gitignore |
| `--include-ignored` | — | Always scan these paths even if ignored |

## `trimemo search`

Find anything by semantic search.

```bash
trimemo search "query"
trimemo search "query" --wing myapp
trimemo search "query" --wing myapp --room auth
trimemo search "query" --results 10
```

| Option | Default | Description |
|--------|---------|-------------|
| `"query"` | — | What to search for |
| `--wing` | all | Filter by wing |
| `--room` | all | Filter by room |
| `--results` | `5` | Number of results |

## `trimemo split`

Split concatenated transcript mega-files into per-session files.

```bash
trimemo split <dir>
trimemo split <dir> --dry-run
trimemo split <dir> --min-sessions 3
trimemo split <dir> --output-dir ~/split-output/
```

| Option | Default | Description |
|--------|---------|-------------|
| `<dir>` | — | Directory with transcript files |
| `--output-dir` | same dir | Write split files here |
| `--dry-run` | — | Preview without writing |
| `--min-sessions` | `2` | Only split files with N+ sessions |

## `trimemo wake-up`

Show L0 + L1 wake-up context (~600–900 tokens).

```bash
trimemo wake-up
trimemo wake-up --wing driftwood
```

| Option | Description |
|--------|-------------|
| `--wing` | Project-specific wake-up |

## `trimemo compress`

Compress drawers using AAAK Dialect.

```bash
trimemo compress --wing myapp
trimemo compress --wing myapp --dry-run
trimemo compress --config entities.json
```

| Option | Description |
|--------|-------------|
| `--wing` | Wing to compress (default: all) |
| `--dry-run` | Preview without storing |
| `--config` | Entity config JSON file |

## `trimemo status`

Show what's been filed — drawer count, wing/room breakdown.

```bash
trimemo status
```

## `trimemo repair`

Rebuild palace vector index from stored data. Fixes segfaults after database corruption.

```bash
trimemo repair
```

Creates a backup at `<palace_path>.backup` before rebuilding, replacing any backup already there.

| Flag | Description |
|------|-------------|
| `rebuild-index` | Positional alias for `--mode from-sqlite --archive-existing` |
| `--mode` | `legacy` (default), `max-seq-id`, or `from-sqlite` |
| `--dry-run` | Print what the repair would do and exit without modifying the palace |
| `--yes` | Skip confirmation for destructive changes |
| `--backup` | Back up SQLite before mutation (default: on) |
| `--source` | Source palace for `--mode from-sqlite` (defaults to `--palace`) |
| `--archive-existing` | Rename the existing palace to `<palace>.pre-rebuild-<timestamp>` first |
| `--segment` | Segment UUID filter for `--mode max-seq-id` |
| `--from-sidecar` | Pre-corruption `chroma.sqlite3` to copy clean `max_seq_id` values from |
| `--confirm-truncation-ok` | Override the truncation safety guard. Disables the abort that protects you when the collection layer returns fewer drawers than SQLite holds |

## `trimemo mcp`

Helper command that outputs setup syntax (like `claude mcp add...`) to connect TriMemo to your AI client, automatically handling paths.

```bash
trimemo mcp
trimemo mcp --palace ~/.custom-palace
```

## `trimemo hook`

Run hook logic for Claude Code / Codex integration.

```bash
trimemo hook run --hook stop --harness claude-code
trimemo hook run --hook precompact --harness claude-code
trimemo hook run --hook session-start --harness codex
```

| Option | Values | Description |
|--------|--------|-------------|
| `--hook` | `session-start`, `stop`, `precompact` | Hook name |
| `--harness` | `claude-code`, `codex` | Harness type |

## `trimemo instructions`

Output skill instructions to stdout.

```bash
trimemo instructions init
trimemo instructions search
trimemo instructions mine
trimemo instructions help
trimemo instructions status
```

## `trimemo rules`

Render the canonical shared-brain system-prompt block, marker-wrapped so
a later re-render can replace it in place. Identity is
`host:harness:project` (stable lowercase tokens). `--project` is the
example workspace name; the block tells the agent to compose the project
component from the current workspace.

```bash
trimemo rules --host mac --harness claude --project myapp
trimemo rules --host windows --harness grok --project trimemo --mcp light
```

`--mcp full` (default) names the 45-tool `trimemo-mcp` tools.
`--mcp light` names the 3-tool triad. Prose is identical.

## `trimemo logstream`

Agent coordination events — delegate work, wait for replies, acknowledge
outcomes (RFC 003). Operates on `logstream.sqlite3` in the palace directory;
safe to run alongside a live hub. See [Agent Logstream](/concepts/agent-logstream).

```bash
trimemo logstream append --type task.request --stream project/myapp \
  --room delegation --from-agent mac --to-agent windows \
  --correlation-id task_123 --body "Please fix the flaky test."

trimemo logstream list --stream project/myapp --room delegation --json
trimemo logstream wait --correlation-id task_123 --type patch.ready \
  --timeout-ms 300000 --json
trimemo logstream ack evt_... --from-agent mac --status applied

# Background watcher: blocks, wakes on what needs you, exits 0 on a match
trimemo logstream watch --agent mac:claude:myapp --type task.request --type task.reply --type patch.ready \
  --json
```

| Subcommand | Description |
|------------|-------------|
| `append` | Append an immutable event (`--type`, `--stream`, `--room`, `--from-agent` required; `--body`/`--body-file`, `--artifact-id` repeatable) |
| `list` | List events, oldest first (all routing fields as filters, `--since-event-id`, `--limit`) |
| `wait` | Long-poll until a match or timeout (`--timeout-ms`, max 300000; exits `2` on timeout) |
| `watch` | Background watcher: re-arms past the `wait` cap, carries the cursor, and exits `0` on a match / `2` on `--idle-exit-ms`. `--agent ID` is shorthand for `--to-agent ID --exclude-from-agent ID` so your own `*` broadcasts never wake you. Filters repeat to mean "or"; `--state-file` resumes exactly (defaults from `--agent`, with `_` doubled and `:` sanitized to `_`); `--follow` stays alive past the first match; a cursorless first run starts at the tip (`--from-start` to replay); exits `130` if interrupted; `--follow --json` emits NDJSON — one batch envelope per line (`{"events": [...], "count": N, "cursor": ...}`), not one event per line |
| `ack` | Append an `event.ack` for an event (`--from-agent` required, `--status`, `--body`) |
| `sync` | Pull missing events/artifacts from peer replicas (`--peer URL --token T`, or all peers in `peers.json`) |

All subcommands accept `--json` for scriptable output.

## `trimemo task`

High-level task creation and controlled execution over the logstream. This
interface creates the complete canonical `task.request` envelope and prints a
short handoff that can be pasted into a destination agent; callers do not need
to construct event fields or correlation ids themselves. Like the other
logstream CLI commands, it operates on the local palace. A client connected to
a remote shared-brain hub should call the equivalent
`mempalace_task_create` MCP tool so the task is appended on the hub.

```bash
trimemo task create \
  --project myapp \
  --from-agent mac-claude \
  --to-agent windows-codex \
  --goal "Fix the flaky integration test." \
  --branch fix/flaky-integration \
  --base-commit 2668053 \
  --done "The focused test passes and a patch is submitted."
```

The command appends an immutable `task.request`, generates a
`task_<goal>_<entropy>` correlation id, and prints a `Ready to paste` line.
Use `--goal-file` or `--done-file` when the exact text is multiline. `--json`
returns `{"task": <event>, "handoff": <line>}`.
`--base-commit` must be an immutable hexadecimal object id (abbreviated or
full), not a branch or tag whose target could move after the event is stored.

An explicitly controlled workflow can start a supported headless runner from
the stored task:

```bash
trimemo task launch task_fix_the_flaky_integration_test_7f3a9c10 \
  --runner codex --workspace /path/to/trusted/checkout
```

For a remote-only MCP client, fetch the full single `task.request` event through
`mempalace_event_list`, save the exact event object as JSON on the destination
machine, and use `--task-file` instead of a task id. This avoids accidentally
resolving the task from an unrelated local palace:

```bash
trimemo task launch --task-file task-request.json \
  --runner codex --workspace /path/to/trusted/checkout
```

Supported runners are `codex` and `claude`. The launcher verifies the task's
addressed identity, refuses to override it, rejects a runner that conflicts
with a conventional `*-codex` or `*-claude` identity, releases its logstream
connection, and starts the runner without a shell. Broadcast tasks require a
concrete `--agent`. It does not add permission-bypass flags or weaken the
runner's sandbox and approval policy.

| Subcommand | Description |
|------------|-------------|
| `create` | Append a canonical task request and print a pasteable handoff (`--project`, `--from-agent`, `--to-agent`, `--goal`/`--goal-file`, `--branch`, `--base-commit`, and `--done`/`--done-file`) |
| `launch` | Resolve and execute an existing task with `--runner codex\|claude` in a trusted `--workspace`; `--agent` accepts broadcasts but cannot impersonate an addressed worker |

## `trimemo artifact`

Exact artifact exchange for agent handoffs — unified diffs, files, logs.
Content is stored verbatim with a SHA-256.

```bash
git diff | trimemo artifact put --kind patch --created-by windows --json
trimemo artifact get art_... | git apply --3way
trimemo artifact get art_... --out /tmp/handoff.patch
```

| Subcommand | Description |
|------------|-------------|
| `put` | Store content (`--kind patch\|file\|log\|json\|note`, `--created-by` required; `--content`, `--file`, or stdin) |
| `get` | Print exact content to stdout, or `--out FILE`; `--json` for metadata |
