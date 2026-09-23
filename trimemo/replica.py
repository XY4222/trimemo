"""
replica.py — Per-palace replica identity (RFC 004 transport seam / provenance)

Every palace replica has one stable ``ReplicaId``, stamped as
``origin_replica`` into every op it authors. For the step-0 pilot the id is
minted locally on first use and persisted in ``replica.json`` inside the
palace directory. Existing 12-hex pilot ids remain valid, but new ids use
128 bits of entropy. When the transport layer lands (MeshGuard), the mesh
Ed25519 identity supersedes it via an alias op — RFC 004 Appendix A.4:
"a rename is just another provenance fact."

The id never syncs and never rotates silently; it names the seat (this
machine's copy of the palace), not the model or the agent.
"""

import json
import os
import re
import secrets
import time
from pathlib import Path

REPLICA_FILENAME = "replica.json"

_REPLICA_ID_RE = re.compile(r"^rep_(?:[0-9a-f]{12}|[0-9a-f]{32})$")

# How long a racer that lost the mint race waits for the winner's file to
# become readable. Only the no-hard-link fallback can expose a partial file,
# so this normally expires instantly.
_ADOPT_TIMEOUT_S = 1.0
_ADOPT_POLL_S = 0.05


def _mint() -> str:
    return f"rep_{secrets.token_hex(16)}"


def _read_replica_id(path: Path) -> str:
    """Return the persisted identity, or raise ValueError with a loud reason."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        replica_id = data["replica_id"]
    except (ValueError, KeyError, TypeError) as exc:
        raise ValueError(
            f"{path} is corrupt ({exc}); refusing to mint a second replica "
            "identity for this palace — restore or delete the file explicitly"
        ) from None
    if not isinstance(replica_id, str) or not _REPLICA_ID_RE.match(replica_id):
        raise ValueError(
            f"{path} holds an invalid replica_id {replica_id!r}; refusing to "
            "mint a second identity — restore or delete the file explicitly"
        )
    return replica_id


def _adopt_published(path: Path) -> str:
    """Read the identity a racing process just published.

    Losing a once-per-palace race is not an error: adopt the winner's id
    instead of forking provenance with a second one. The in-place fallback in
    :func:`get_replica_id` can briefly expose a partial file, so retry instead
    of failing the caller outright.
    """
    deadline = time.monotonic() + _ADOPT_TIMEOUT_S
    while True:
        try:
            return _read_replica_id(path)
        except ValueError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(_ADOPT_POLL_S)


def get_replica_id(palace_path: str) -> str:
    """Return this palace's stable replica id, minting it on first use.

    Exactly one identity per seat, even under concurrent first use: the
    ``path.exists()`` check below is only a fast path — two processes can both
    miss the file — so the id is *published* exclusively (see below) and a
    racer that loses adopts the winner's id rather than keeping its own. Two
    ids for one replica would fork its op-log provenance.
    """
    path = Path(os.path.expanduser(palace_path)) / REPLICA_FILENAME
    if path.exists():
        return _read_replica_id(path)

    path.parent.mkdir(parents=True, exist_ok=True)
    replica_id = _mint()
    payload = (
        json.dumps({"replica_id": replica_id, "minted_at_note": "RFC 004 step 0"}, indent=2) + "\n"
    )
    # Write to a *unique* temp file first. A shared "replica.json.tmp" let two
    # concurrent minters clobber each other's bytes, after which one could
    # rename the other's half-written file into place as the identity.
    tmp = path.with_name(f"{path.name}.{os.getpid()}.{secrets.token_hex(4)}.tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        try:
            # Atomic publish that fails on an existing destination: exactly
            # one racer wins, and the file it lands is fully written.
            os.link(tmp, path)
            return replica_id
        except FileExistsError:
            return _adopt_published(path)
        except OSError:
            pass  # filesystem has no hard links — fall back below
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            return _adopt_published(path)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        return replica_id
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass
