#!/usr/bin/env sh
# Flexible entrypoint: pick the MCP server or the CLI from the first argument.
#
#   docker run -i trimemo                  -> MCP server over stdio (default)
#   docker run -i trimemo mcp              -> MCP server over stdio (explicit)
#   docker run trimemo cli search "query"  -> CLI passthrough (explicit)
#   docker run trimemo search "query"      -> CLI passthrough (implicit)
#
# `mcp` and `cli` are dispatch keywords; anything else is forwarded to the
# `trimemo` CLI verbatim so subcommands like `mine`, `search`, `wake-up`
# work without ceremony.
set -e

case "${1:-mcp}" in
    mcp)
        if [ "$#" -gt 0 ]; then
            shift
        fi
        exec trimemo-mcp "$@"
        ;;
    cli)
        if [ "$#" -gt 0 ]; then
            shift
        fi
        exec trimemo "$@"
        ;;
    *)
        exec trimemo "$@"
        ;;
esac
