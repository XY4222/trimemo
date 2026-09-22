# Android / Termux

TriMemo does not currently install directly into Termux's Android Python.
Its compiled dependencies publish Linux wheels, while Termux uses Android's
Bionic libc and Android wheel tags. `pip` therefore falls back to source builds
that may fail in dependencies such as ChromaDB or Maturin.

The tested compatibility route is to run the normal Linux ARM64 packages in a
Debian PRoot container. This is not a native Android port. The recipe below was
tested on Android ARM64 with Termux, Debian 12, Python 3.11, and the
`sqlite_exact` backend.

## Before you start

- Use a current Termux build and a 64-bit ARM device.
- Allow at least 2 GB of free space for the Debian root filesystem, Python
  environment, dependencies, and embedding model.
- Keep the palace inside the PRoot container. Only bind the Termux directories
  that TriMemo needs to read.

PRoot is a compatibility layer, not a security boundary. The launcher below
uses isolated mode and exposes only the Termux home directory, but TriMemo can
still read everything under that bind.

## Install the container

Run these commands in Termux:

```bash
pkg update
pkg install proot-distro
proot-distro install -n trimemo debian:12
```

Then install TriMemo into a dedicated virtual environment inside Debian:

```bash
proot-distro login --isolated trimemo -- /bin/sh -lc '
  set -eu
  apt-get update
  apt-get install -y --no-install-recommends ca-certificates python3 python3-venv
  mkdir -p /opt/trimemo/home /opt/trimemo/cache /opt/trimemo/palace
  python3 -m venv /opt/trimemo/venv
  /opt/trimemo/venv/bin/python -m pip install --upgrade pip
  /opt/trimemo/venv/bin/python -m pip install --only-binary=:all: trimemo
'
```

`--only-binary=:all:` makes the installation fail clearly instead of starting
an unsupported source build if a future dependency has no Linux ARM64 wheel.

## Add a launcher

Save the following script as `~/.local/bin/trimemo-proot` in Termux, then run
`chmod 700 ~/.local/bin/trimemo-proot`:

```bash
#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

termux_home="${HOME:?}"
case "$termux_home" in
  /*) ;;
  *) echo "HOME must be an absolute path" >&2; exit 2 ;;
esac
case "$termux_home" in
  *:*) echo "HOME containing ':' cannot be bound safely" >&2; exit 2 ;;
esac

case "$PWD" in
  "$termux_home"|"$termux_home"/*) work_dir="$PWD" ;;
  *) work_dir="$termux_home" ;;
esac

exec "${PREFIX:?}/bin/proot-distro" login \
  --isolated \
  --bind "$termux_home:$termux_home" \
  --work-dir "$work_dir" \
  trimemo -- \
  env -i \
    HOME=/opt/trimemo/home \
    PATH=/opt/trimemo/venv/bin:/usr/bin:/bin \
    LANG=C.UTF-8 LC_ALL=C.UTF-8 \
    XDG_CACHE_HOME=/opt/trimemo/cache \
    MEMPALACE_PALACE_PATH=/opt/trimemo/palace \
    MEMPALACE_BACKEND=sqlite_exact \
    MEMPALACE_EMBEDDING_MODEL=minilm \
    MEMPALACE_EMBEDDING_DEVICE=cpu \
    MEMPALACE_EMBEDDING_THREADS=1 \
    OMP_NUM_THREADS=1 TOKENIZERS_PARALLELISM=false \
    /opt/trimemo/venv/bin/trimemo "$@"
```

The wrapper preserves every command-line argument and the current working
directory when it is under the Termux home directory. It uses the bundled
`sqlite_exact` backend to avoid relying on ChromaDB's embedded storage runtime
under PRoot, while keeping embedding and retrieval local to the device. One
embedding thread is a conservative default for phone thermals.

## Verify and use it

```bash
trimemo-proot --version

# Project files under the Termux home bind
trimemo-proot mine "$HOME/projects/myapp"

# Codex conversations
trimemo-proot mine "$HOME/.codex/sessions" --mode convos

trimemo-proot search "why did we change the authentication flow"
```

The first mine or search downloads the local MiniLM model (about 80 MB). A
warning about denied access to `/sys/class/drm` can appear under PRoot; it is
harmless when `MEMPALACE_EMBEDDING_DEVICE=cpu` is set as above.

Paths outside the Termux home directory are deliberately unavailable. Copy the
source under `$HOME`, or add a narrow, explicit `--bind source:destination` to
the launcher after considering what that exposes.

## Upgrade

Upgrade only the Python environment; the palace remains under
`/opt/trimemo/palace`:

```bash
proot-distro login --isolated trimemo -- \
  /opt/trimemo/venv/bin/python -m pip install \
  --upgrade --only-binary=:all: trimemo
```

Back up the container before removing or resetting it. Both
`proot-distro remove trimemo` and `proot-distro reset trimemo` destroy the
palace stored inside the container.
