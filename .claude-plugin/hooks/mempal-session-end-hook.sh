#!/bin/bash
# TriMemo SessionEnd Hook — thin wrapper calling the Python CLI.
#
# Claude Code documents a default SessionEnd hook timeout of 1.5s, and
# "timeouts set on plugin-provided hooks do not raise the budget"
# (https://code.claude.com/docs/en/hooks). A cold `trimemo` start alone
# exceeds 1.5s, so the final mine must NOT run in the foreground — it would be
# killed before it saved anything. Unlike the foreground Stop/PreCompact plugin
# wrappers, this one backgrounds the hook and returns immediately; the detached
# child finishes the save after the session has exited. All logic lives in
# mempalace.hooks_cli for cross-harness extensibility.
run_mempalace_hook() {
  if command -v trimemo >/dev/null 2>&1; then
    exec trimemo hook run "$@"
  fi

  MEMPAL_PYTHON_BIN="${MEMPAL_PYTHON:-}"
  if [ -z "$MEMPAL_PYTHON_BIN" ] || [ ! -x "$MEMPAL_PYTHON_BIN" ]; then
    MEMPAL_PYTHON_BIN="$(command -v python3 2>/dev/null || echo python3)"
  fi
  if "$MEMPAL_PYTHON_BIN" -c "import trimemo" >/dev/null 2>&1; then
    exec "$MEMPAL_PYTHON_BIN" -m trimemo hook run "$@"
  fi

  if command -v python >/dev/null 2>&1 && python -c "import trimemo" >/dev/null 2>&1; then
    exec python -m trimemo hook run "$@"
  fi

  echo "TriMemo hook error: could not find a runnable trimemo command or module" >&2
  exit 1
}

# Capture stdin (the SessionEnd JSON) before backgrounding — the parent's
# stdin is gone once we return. Forward it to the detached worker, which runs
# the final mine on its own time and outlives this process.
payload="$(cat)"
(
  printf '%s' "$payload" | run_mempalace_hook --hook session-end --harness "${MEMPALACE_HOOK_HARNESS:-claude-code}"
) >/dev/null 2>&1 </dev/null &
disown 2>/dev/null || true

# Return immediately so the harness never blocks on session exit.
printf '{}'
