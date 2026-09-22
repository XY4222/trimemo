#!/bin/bash
# TriMemo PreCompact Hook — thin wrapper calling Python CLI
# All logic lives in mempalace.hooks_cli for cross-harness extensibility
run_mempalace_hook() {
  if command -v trimemo >/dev/null 2>&1; then
    trimemo hook run "$@"
    return $?
  fi

  if command -v python3 >/dev/null 2>&1 && python3 -c "import trimemo" >/dev/null 2>&1; then
    python3 -m trimemo hook run "$@"
    return $?
  fi

  if command -v python >/dev/null 2>&1 && python -c "import trimemo" >/dev/null 2>&1; then
    python -m trimemo hook run "$@"
    return $?
  fi

  echo "TriMemo hook error: could not find a runnable trimemo command or module" >&2
  return 1
}

run_mempalace_hook --hook precompact --harness claude-code
