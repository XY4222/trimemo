# TriMemo Cursor Plugin

A Cursor IDE plugin that gives your agent a persistent memory system. Auto-registers the `trimemo-mcp` server (45 MCP tools), ships 5 slash commands, three model-invocable skills (setup, recall, and logstream tasks), and an optional recall rule.

> Hooks (auto-save + session-start memory recall) are shipped separately under `hooks/cursor/` so the plugin is safe to install in any Cursor workspace without touching the agent loop. See [Hooks](#hooks-optional) below.

## Prerequisites

- Python 3.9+
- Cursor 1.7+ (plugin manifest schema requires it)

## Installation

### Local clone (recommended while not in the marketplace yet)

Symlink (or copy) this repository into Cursor's local plugins folder:

```bash
ln -s /path/to/trimemo ~/.cursor/plugins/local/trimemo
```

Then in Cursor: <kbd>Cmd</kbd>-<kbd>Shift</kbd>-<kbd>P</kbd> → **Developer: Reload Window**.

### Marketplace

Once published, install via the Cursor marketplace panel and select `trimemo`. Required-plugin distribution from a team marketplace is also supported.

## Post-Install Setup

After installing the plugin, run the `init` command in a Cursor chat:

```
/trimemo-init
```

(Or just say "use the trimemo skill" — Cursor will model-invoke the bundled skill.)

This installs the `trimemo` package via `uv tool` or `pip`, initializes a palace under `~/.mempalace/`, and verifies the MCP server is reachable.

## Available Slash Commands

| Command             | Description                                                                       |
|---------------------|-----------------------------------------------------------------------------------|
| `/trimemo-help`   | Show available tools, skills, CLI commands, hooks, and architecture               |
| `/trimemo-init`   | Set up TriMemo — install, configure, onboard                                    |
| `/trimemo-search` | Search your memories across the palace using semantic search                      |
| `/trimemo-mine`   | Mine projects and conversations into the palace                                   |
| `/trimemo-status` | Show palace overview — wings, rooms, drawer counts                                |

> Cursor commands are global, not plugin-namespaced — that's why each slug is prefixed with `trimemo-` rather than appearing as `/help`, `/init`, etc. This keeps them collision-free with built-in or other-plugin commands.

## Skills

Two model-invocable skills ship at the plugin root under `skills/`:

| Skill | What it does |
|-------|--------------|
| `trimemo` | Setup, mining, status, and the dynamic `trimemo instructions` CLI. |
| `trimemo-recall` | Search-before-answer protocol — makes the agent read the palace before answering about past work, people, projects, or prior decisions instead of guessing. |

Cursor surfaces these automatically when a request matches their description, or you can attach them explicitly.

## Recall rule (optional)

The plugin also ships a Cursor rule at the plugin root under `rules/trimemo-recall.mdc`:

```yaml
description: When the user asks about past work, prior decisions, people, ... call mempalace_search before answering ...
alwaysApply: false
```

It is `alwaysApply: false` on purpose — Cursor loads it only when its matcher judges the turn recall-relevant, so it never fires on unrelated coding work and never adds MCP latency to greenfield tasks. The rule, the `trimemo-recall` skill, and the `sessionStart` hook all reference the same canonical protocol in [`integrations/shared/recall-protocol.md`](../integrations/shared/recall-protocol.md).

Want recall forced into **every** conversation regardless of context? Copy the aggressive `alwaysApply: true` variant from [`examples/cursor/rules/`](../examples/cursor/rules/README.md) into `~/.cursor/rules/`. That is a deliberate, heavier opt-in, not a default.

## MCP Server

This plugin ships `mcp.json` at the plugin root, so Cursor auto-loads the `trimemo-mcp` server on plugin install:

```json
{
  "mcpServers": {
    "trimemo": {
      "command": "trimemo-mcp"
    }
  }
}
```

All 45 TriMemo MCP tools (`mempalace_search`, `mempalace_add_drawer`, `mempalace_diary_write`, `mempalace_check_duplicate`, `mempalace_diary_read`, …) become available to the agent immediately. No manual `~/.cursor/mcp.json` edit required.

If the server doesn't appear, confirm `trimemo-mcp` is on the user `$PATH`:

```bash
command -v trimemo-mcp
```

If it isn't, run `/init` (or `trimemo install` from a terminal) — `trimemo-mcp` is installed alongside the `trimemo` package.

## Hooks (optional)

Cursor's hooks system is configured separately from plugins (in `~/.cursor/hooks.json` or `.cursor/hooks.json`), so this plugin does **not** wire hooks itself. The TriMemo repository ships three Cursor-native hooks under [`hooks/cursor/`](../hooks/cursor/) that you install with one command.

User scope — writes `~/.cursor/hooks.json`, applies to every Cursor workspace (recommended):

```bash
hooks/cursor/install.sh --scope user --variant full
```

Project scope — writes `.cursor/hooks.json` under the current project only:

```bash
hooks/cursor/install.sh --scope project --variant full
```

What you get:

| Hook event     | What it does                                                                                          |
|----------------|-------------------------------------------------------------------------------------------------------|
| `sessionStart` | Injects an `additional_context` recap of relevant memories scoped to the workspace wing               |
| `stop`         | Counts agent turns; every N turns, emits a `followup_message` instructing a memory checkpoint         |
| `preCompact`   | Synchronously mines the transcript before compaction, drops a marker so the next `stop` saves a diary |

Full details: [`website/guide/cursor-hooks.md`](../website/guide/cursor-hooks.md) and [`hooks/cursor/README.md`](../hooks/cursor/README.md).

## Uninstall

Remove the local plugin symlink:

```bash
rm ~/.cursor/plugins/local/trimemo
```

Then in Cursor: <kbd>Cmd</kbd>-<kbd>Shift</kbd>-<kbd>P</kbd> → **Developer: Reload Window**.

If you also installed the hooks, remove them (leaves any unrelated hooks in `hooks.json` untouched):

```bash
hooks/cursor/install.sh --scope user --uninstall
```

## Full Documentation

See the main [README](../README.md) for complete documentation, architecture details, and advanced usage.
