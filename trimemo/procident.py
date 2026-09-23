"""Cross-platform process identity — is this pid still *the same* process?

A bare pid does not identify a process. The OS recycles pids after a crash, so
"the pid is alive" is not the same as "the process that wrote this record is
alive". A stale daemon registration, writer lease or ``serverinfo.json`` whose
pid was handed to an unrelated process would otherwise read as live — and for
the HTTP hub registry that means the palace bearer token is sent to whatever
now holds the port.

The gap is closed with the process *start time*: a process that started after a
record was written cannot be the one that wrote it. Both the daemon
registration (#2442) and the hub registry (:mod:`trimemo.server_registry`) rely
on that comparison.

Deliberately stdlib-only and free of intra-package imports, so the CLI, the
hooks and the daemon can all import it without pulling in a heavier module.
"""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

# A process that started after a record was written cannot be the process that
# wrote it. The slack absorbs timestamp granularity between the process start
# clock and file modification times.
START_TIME_SLACK_SECONDS = 2.0


def pid_alive(pid) -> bool:
    """Liveness probe for ``pid`` that never signals it.

    ``os.kill(pid, 0)`` is NOT a harmless existence check on Windows: signal 0
    is ``signal.CTRL_C_EVENT``, so Python routes it to
    ``GenerateConsoleCtrlEvent`` and sends a Ctrl-C to the target's process
    group instead of probing the pid. On a process with an attached console
    (e.g. a CI runner) that Ctrl-C is delivered back to *this* interpreter and
    surfaces as a spurious ``KeyboardInterrupt``. Windows therefore probes via
    the Win32 process-handle API, which has no signalling side effects.
    """
    if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0:
        return False
    if os.name == "nt":
        try:
            return _pid_alive_windows(pid)
        except OSError:
            # If the Win32 probe itself fails, assume alive rather than risk
            # discarding a healthy endpoint — and never fall back to os.kill.
            return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _pid_alive_windows(pid: int) -> bool:
    """Signal-free Windows liveness probe via the process-handle API."""
    import ctypes
    from ctypes import wintypes

    SYNCHRONIZE = 0x00100000
    WAIT_TIMEOUT = 0x00000102
    ERROR_ACCESS_DENIED = 5

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel32.WaitForSingleObject.restype = wintypes.DWORD
    kernel32.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)

    handle = kernel32.OpenProcess(SYNCHRONIZE, False, int(pid))
    if not handle:
        # No handle: access-denied means the process exists but isn't ours to
        # open; any other error (invalid parameter / not found) means it's gone.
        return ctypes.get_last_error() == ERROR_ACCESS_DENIED
    try:
        # A live process is not signalled, so the zero-timeout wait returns
        # WAIT_TIMEOUT; an exited process is signalled and returns WAIT_OBJECT_0.
        return kernel32.WaitForSingleObject(handle, 0) == WAIT_TIMEOUT
    finally:
        kernel32.CloseHandle(handle)


def process_start_time(pid: int) -> float | None:
    """When ``pid`` started, as a Unix timestamp, or None when it cannot be read.

    Used to tell a live registered process from an unrelated process that has
    since been given the same pid. ``psutil`` is only a development dependency,
    so it is used when present and the platform source otherwise.
    """
    if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0:
        return None
    try:
        import psutil  # type: ignore[import-not-found]
    except ImportError:
        psutil = None
    if psutil is not None:
        try:
            return float(psutil.Process(int(pid)).create_time())
        except Exception:
            return None
    if os.name == "nt":
        try:
            return _process_start_time_windows(pid)
        except OSError:
            return None
    if Path("/proc/self/stat").exists():
        return _process_start_time_linux(pid)
    return _process_start_time_ps(pid)


def started_after(pid, reference_time: float, *, slack: float | None = None) -> bool:
    """True when ``pid`` provably started after ``reference_time``.

    A process that started after a record was written cannot be the process
    that wrote it, so any pid-based trust in that record must be dropped.
    Returns False when the start time cannot be read: refusing is recoverable,
    discarding a live owner's record is not (#2442).
    """
    if slack is None:
        slack = START_TIME_SLACK_SECONDS
    started = process_start_time(pid)
    if started is None:
        return False
    return started > reference_time + slack


def _process_start_time_windows(pid: int) -> float | None:
    """Creation time of ``pid`` as a Unix timestamp via ``GetProcessTimes``."""
    import ctypes
    from ctypes import wintypes

    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    filetime_p = ctypes.POINTER(wintypes.FILETIME)
    kernel32.GetProcessTimes.restype = wintypes.BOOL
    kernel32.GetProcessTimes.argtypes = (
        wintypes.HANDLE,
        filetime_p,
        filetime_p,
        filetime_p,
        filetime_p,
    )
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)

    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid))
    if not handle:
        return None
    try:
        creation, exited, kernel, user = (wintypes.FILETIME() for _ in range(4))
        ok = kernel32.GetProcessTimes(
            handle,
            ctypes.byref(creation),
            ctypes.byref(exited),
            ctypes.byref(kernel),
            ctypes.byref(user),
        )
        if not ok:
            return None
        ticks = (creation.dwHighDateTime << 32) | creation.dwLowDateTime
        # FILETIME counts 100 ns intervals since 1601-01-01.
        return ticks / 10_000_000 - 11_644_473_600
    finally:
        kernel32.CloseHandle(handle)


def _process_start_time_linux(pid: int) -> float | None:
    """Start time of ``pid`` from ``/proc`` (boot time plus clock ticks)."""
    try:
        stat = Path(f"/proc/{int(pid)}/stat").read_text(encoding="utf-8")
        # The command name can contain spaces and parentheses; fields resume
        # after the last ")". starttime is field 22, index 19 from "state".
        fields = stat[stat.rindex(")") + 2 :].split()
        start_ticks = int(fields[19])
        boot = next(
            int(line.split()[1])
            for line in Path("/proc/stat").read_text(encoding="utf-8").splitlines()
            if line.startswith("btime ")
        )
        return boot + start_ticks / os.sysconf("SC_CLK_TCK")
    except (OSError, ValueError, IndexError, StopIteration):
        return None


def _process_start_time_ps(pid: int) -> float | None:
    """Start time of ``pid`` from ``ps -o lstart=`` (macOS and other POSIX)."""
    try:
        out = subprocess.run(
            ["ps", "-o", "lstart=", "-p", str(int(pid))],
            capture_output=True,
            text=True,
            timeout=2,
            env={**os.environ, "LC_ALL": "C"},
            check=False,
        ).stdout.strip()
        if not out:
            return None
        return time.mktime(time.strptime(out, "%a %b %d %H:%M:%S %Y"))
    except (OSError, ValueError, subprocess.SubprocessError):
        return None
