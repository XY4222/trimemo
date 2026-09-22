# TriMemo - Codex CLI Plugin

Give your AI a persistent memory -- mine projects and conversations into a searchable palace backed by ChromaDB, with 44 MCP tools, auto-save hooks, and guided skills.

## Prerequisites

- Python 3.9+
- Codex CLI installed and configured
- `uv tool install trimemo` (recommended) or `pip install trimemo`

## Installation

1. Add the repo to the Codex marketplaces:

```bash
codex plugin marketplace add TriMemo/trimemo
```

2. Install the plugin:

```bash
codex plugin add trimemo@trimemo
```

3. Initialize your palace in the Codex TUI:

```bash
codex
> $trimemo:trimemo init
```

## Available Skills

| Skill | Description |
|-------|-------------|
| `$trimemo:trimemo` | Install, configure, and operate TriMemo, including a private local palace, a shared-brain hub, or a client joining an existing hub |
| `$trimemo:trimemo-recall` | Recall protocol for TriMemo — search the palace before answering about past work, people, projects, or prior decisions |
| `$trimemo:trimemo-task` | Create, hand off, claim, execute, and close agent tasks through the TriMemo logstream |

### Skill Commands

The main `$trimemo:trimemo` skill can be invoked with five different subcommands. `$trimemo <command>` can be used as a short form invocation. 

| Command | Description |
|---------| ------------|
| `$trimemo help` | Show available commands and usage tips |
| `$trimemo init` | Initialize a new memory palace |
| `$trimemo search` | Semantic search across all mined memories |
| `$trimemo mine` | Mine a project or conversation into your palace |
| `$trimemo status` | Show palace status, room counts, and health |

## Hooks

The plugin includes auto-save hooks that run on session stop (every 15 messages) and before context compaction, automatically preserving conversation context into your palace.

Set the `MEMPAL_DIR` environment variable to a directory path to automatically run `trimemo mine` on that directory during each save trigger.

## Support

- Repository: https://github.com/MemPalace/trimemo
- Issues: https://github.com/MemPalace/trimemo/issues
