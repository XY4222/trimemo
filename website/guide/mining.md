# Mining Your Data

TriMemo ingests your data by **mining** — scanning files and filing their content as verbatim drawers in the palace.

## Mining Modes

### Projects Mode (default)

Scans code, docs, and notes. Respects `.gitignore` by default.

```bash
trimemo mine ~/projects/myapp
```

Each file becomes a drawer, tagged with a wing (project name) and room (topic). Rooms are auto-detected from your folder structure during `trimemo init`.

Options:
```bash
# Override wing name
trimemo mine ~/projects/myapp --wing myapp

# Ignore .gitignore rules
trimemo mine ~/projects/myapp --no-gitignore

# Include specific ignored paths
trimemo mine ~/projects/myapp --include-ignored dist,build

# Limit number of files
trimemo mine ~/projects/myapp --limit 100

# Preview without filing
trimemo mine ~/projects/myapp --dry-run
```

### Conversations Mode

Indexes conversation exports from Claude, ChatGPT, Slack, and other tools. Chunks by exchange pair (human + assistant turns).

```bash
trimemo mine ~/chats/ --mode convos
```

Supports five chat formats automatically:
- Claude JSON exports
- ChatGPT exports
- Slack exports
- Markdown conversations
- Plain text transcripts

### General Extraction

Auto-classifies conversation content into five memory types:

```bash
trimemo mine ~/chats/ --mode convos --extract general
```

Memory types:
- **Decisions** — choices made, options rejected
- **Preferences** — habits, likes, opinions
- **Milestones** — sessions completed, goals reached
- **Problems** — bugs, blockers, issues encountered
- **Emotional context** — reactions, concerns, excitement

## Splitting Mega-Files

Some transcript exports concatenate multiple sessions into one huge file. Split them first:

```bash
# Preview what would be split
trimemo split ~/chats/ --dry-run

# Split files with 2+ sessions (default)
trimemo split ~/chats/

# Only split files with 3+ sessions
trimemo split ~/chats/ --min-sessions 3

# Output to a different directory
trimemo split ~/chats/ --output-dir ~/chats-split/
```

::: tip
Always run `trimemo split` before mining conversation files. It's a no-op if files don't need splitting.
:::

## Multi-Project Setup

Mine each project into its own wing:

```bash
trimemo mine ~/chats/orion/  --mode convos --wing orion
trimemo mine ~/chats/nova/   --mode convos --wing nova
trimemo mine ~/chats/helios/ --mode convos --wing helios
```

Six months later:
```bash
# Project-specific search
trimemo search "database decision" --wing orion

# Cross-project search
trimemo search "rate limiting approach"
# → finds your approach in Orion AND Nova, shows the differences
```

## Team Usage

Mine Slack exports and AI conversations for team history:

```bash
trimemo mine ~/exports/slack/ --mode convos --wing driftwood
trimemo mine ~/.claude/projects/ --mode convos
```

Then search across people and projects:
```bash
trimemo search "Soren sprint" --wing driftwood
# → 14 closets: OAuth refactor, dark mode, component library migration
```

## Agent Tag

Every drawer is tagged with the agent that filed it:

```bash
# Default agent name
trimemo mine ~/data/ --agent trimemo

# Custom agent name
trimemo mine ~/data/ --agent reviewer
```

This is used by [Specialist Agents](/concepts/agents) to partition memories.
