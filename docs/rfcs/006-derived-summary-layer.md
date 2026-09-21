# RFC 006: The Derived Summary Layer — Digests, Importance, and a Graph-Fed L1

Status: Draft — full text written 2026-09-21; fact-audit pass 2026-09-21 (all code references re-verified against tree at main; line numbers corrected, dead-code caveat added in §C.1); design-audit pass 2026-09-22 (fixed ingest-time scoring ordering, corrected backfill write primitive to `update`, tightened B.2 timestamp semantics to `valid_from`, added metadata-merge regression test); awaiting review
Owner: 寇豆码 (drafter, with WorkBuddy session); decider TBD
Created: 2026-09-21
Prior art: RFC 004 §7 (derived state category), `docs/CLOSETS.md` (purge-and-rebuild precedent), `mempalace/layers.py` (L0–L3 stack), `mempalace/knowledge_graph.py`
Related discussions: three-tier memory proposal (core profile / summary / fragments) evaluated 2026-09-21 — motivation below

## Summary

MemPalace's wake-up story is weaker than its search story, and the gap is
measurable in three places that already exist in the code:

1. **L1 "Essential Story" is not essential.** `layers.py` sorts drawers by
   an `importance` metadata key that no ingest path ever writes — every
   drawer ties at the default, and the sort collapses to recency. L1 is
   "the 15 most recently filed drawers," not "who this person is and what
   matters."
2. **The knowledge graph never reaches wake-up.** `knowledge_graph.py`
   maintains temporal entity relationships, but `Layer1.generate()` reads
   only the drawers collection. The system's most stable facts are
   invisible to its most visible surface.
3. **There is no compressed session-level view.** Answering "what have we
   been doing" requires either semantic search (hits fragments, not
   narrative) or dumping raw drawers into context (the exact token bloat
   the wake-up budget exists to prevent).

This RFC proposes closing all three with **derived views** — no new storage
tier, no change to the verbatim corpus, no sync surface:

- **Workstream A — importance scoring**: fill the already-read
  `importance` metadata key at ingest and via backfill.
- **Workstream B — graph-fed L1**: L1 generation consumes the knowledge
  graph as its "stable core" section.
- **Workstream C — digest collection**: a per-(wing, room) compressed
  narrative view with `→drawer_id` pointers, structurally identical to
  closets — rebuilt from drawers, never a retrieval target for verbatim
  search, never the only copy of anything.

One sentence: **the palace gains a compressed view layer the way it gained
closets — as a re-derivable index over sacred content, not as a second
store.**

## Motivation

### The three-tier proposal and why it became this RFC

The motivating proposal (2026-09-21) was to restructure memory into three
tiers — a stable core profile, a compressed summary tier, and atomic
fragment retrieval — following the pattern used in multi-user assistant
products built on workflow platforms.

The evaluation against this codebase found:

| Proposal tier | MemPalace today | Verdict |
|---|---|---|
| Fragment memory (atomic pieces, vector retrieval) | Drawers + closets, hybrid search | Already exists — this *is* the product |
| Core profile (stable structured facts) | L0 (manual) + L1 (degenerate, see above) + KG (disconnected) | Real gap, wrong fix: the fix is wiring and scoring, not a new tier |
| Summary memory (compressed conclusions as stored data) | Nothing | Rejected as storage; admitted as *derived view* (this RFC) |

Two constraints from `CLAUDE.md` govern the outcome:

- "**Verbatim always** — Never summarize, paraphrase, or lossy-compress
  user data." And, under Contributing: "We do not accept summarization of
  user content."
- "**100% recall is the design requirement.**"

A summary that becomes a *retrieval target* can shadow the verbatim
original — a query hits the summary's vocabulary, not the user's words,
and recall drops below the line the benchmarks are graded against
(96.6% R@5 raw / 98.4% hybrid v4 on LongMemEval). A summary that is a
*view with pointers* cannot: delete every digest and the palace is
unchanged.

The routing doctrine from the three-tier proposal is retained as design
input, because it is correct:

| Query intent | Route | MemPalace surface |
|---|---|---|
| Verify a fact, recall a detail ("which day did we test-drive?") | Verbatim fragments, exact original words | L3 search over drawers (unchanged) |
| Grasp direction, recommend, orient ("what should we look at next?") | Compressed conclusions, cheap tokens | L1 wake-up + digest views (this RFC) |

### Evidence the gap is real

- `layers.py:198-206` (in-tree comment): "the ingest pipeline … never
  [records] an evaluative importance/weight field. So `importance` is
  absent on virtually every drawer and ties at the default."
- `layers.py:215-224`: L1 reads `importance`, `emotional_weight`, or
  `weight` — all absent — sorts by `filed_at` effectively.
- `knowledge_graph.py` implements `query_entity`, `timeline`,
  `find_entity_candidates`, `supersede` — no caller in `layers.py`.
- Closet precedent: `mempalace/palace/closets.py` already demonstrates the
  derived-collection pattern (build from content, purge-and-rebuild by
  source, pointers in, content out).

## Requirements

- **R1 — Constitution holds.** Drawers remain the only system of record.
  No digest, score, or graph fact is ever the sole copy of user content.
  `mempalace repair rebuild-index` class operations can delete and rebuild
  every artifact this RFC adds with zero information loss.
- **R2 — Zero recall regression.** The default search path (L3 hybrid
  ranking) must not change behavior. Digests are excluded from the
  drawers collection and from ranking signals. Benchmarks must reproduce
  existing numbers bit-for-bit after this RFC lands.
- **R3 — Wake-up budget holds.** Startup injection < 100 ms (CLAUDE.md).
  Digests are precomputed; wake-up reads them, never generates them.
- **R4 — Hook budget holds.** Hooks < 500 ms. Digest builds and importance
  backfills run in `sweep` cadence, daemon idle time, or explicit CLI —
  never inside a hook.
- **R5 — No API key required.** Default digest generation is extractive
  (no LLM). Local-LLM enrichment follows the existing local-first pattern
  (`llm_client.py` / `closet_llm.py`): Ollama-class runtimes by default,
  BYOK external providers only if the user configures them.
- **R6 — Incremental only.** Backfill adds metadata keys via
  `collection.update` (merge semantics, no re-embedding); it never
  deletes or rewrites drawer content. Digest purge-and-rebuild applies
  only to the digest collection (same per-source scope rule as
  `purge_file_closets`).
- **R7 — RFC 004 compatibility.** Digests are Layer-3 derived state in
  RFC 004's taxonomy: rebuilt locally per replica, never synced. If/when
  the op-log lands, digest rebuild is a local fold, not an op kind. Per
  RFC 004 §6.2, if digest state ever needs cross-replica identity it must
  name its own op kinds — this RFC explicitly does not.

## Non-Goals

- **Storing summaries of user content in the verbatim corpus.** Digests
  live in their own collection, are regenerable, and are excluded from
  verbatim retrieval.
- **Multi-user profile modeling.** The user-isolation dimension of the
  three-tier pattern maps to wings, which already exist. There is one
  human per palace; nothing here introduces per-user memory rows.
- **Replacing or auto-generating L0.** `identity.txt` stays hand-written.
- **Cloud summarization by default**, telemetry of any kind, or new
  external dependencies for the core path.
- **Making digests searchable in v1.** Searchable digests are deferred
  (see Open Questions) until R2 can be proven under an adversarial eval.

## Architecture Overview

```
                        ┌──────────────────────────────────────────┐
                        │  DRAWERS (verbatim, untouched)           │
                        │  metadata: wing room filed_at entities … │
                        │  + importance (Workstream A)             │
                        └───────┬───────────────────┬──────────────┘
                                │                   │
              purge-and-rebuild │                   │ read-only consume
                                ▼                   ▼
                   ┌────────────────────┐   ┌──────────────────────┐
                   │ DIGEST collection  │   │ KNOWLEDGE GRAPH      │
                   │ per (wing, room)   │   │ (SQLite, existing)   │
                   │ summary + →drawer  │   │ entities + triples   │
                   └───────┬────────────┘   └──────────┬───────────┘
                           │                           │
                           │  L1 generation reads both, in order:    │
                           ▼                           ▼
                ┌────────────────────────────────────────┐
                │ L1 ESSENTIAL STORY (layers.py)          │
                │  [core] KG top entities + live triples  │
                │  [story] digest texts by room score     │
                │  [fallback] per-drawer scan (today)     │
                └────────────────────────────────────────┘
                L2 / L3 search paths: UNCHANGED (R2)
```

## §A. Workstream A — Importance Scoring

### A.1 Where the key already is

`Layer1` checks `importance`, `emotional_weight`, `weight` per drawer
(`layers.py:215-224`), defaulting to `3.0`. This workstream makes the
first key real. No reader code changes beyond what exists.

### A.2 Score (v1, heuristic, zero LLM)

Two-phase, because of a hard ordering fact in the ingest pipeline: in
`process_file` the drawer batch upsert lands **before** the closet build
(drawers ~`miner.py:1952`, closets ~`miner.py:1977`), so
`closet_pointer_count` cannot exist when `_build_drawer_metadata`
(`miner.py:1697`) runs.

**Phase 1 — at drawer metadata build (ingest):**

```
importance = clamp(1.0, 5.0,
      1.0
    + 0.5 · min(3, len(entities))          # entity density (metadata already carries this, miner.py:1760)
    + 0.4 · min(3, kg_edge_count)          # graph connectivity of those entities
    + 0.2 · interaction_markers            # questions asked, decisions keywords (stoplist-bounded)
)
```

**Phase 2 — finalize after closet build, same mine pass:** the closet
emitter already runs after the upsert with `drawer_ids` in hand; it adds
the missing term via a metadata-only update:

```
importance += 0.3 · min(2, closet_pointer_count)   # topic salience
```

- `entities`: already extracted into metadata by
  `_extract_entities_for_metadata` — free at ingest.
- `kg_edge_count`: one indexed lookup per entity in the local KG.
- `closet_pointer_count`: counted during closet build (Workstream C
  shares the pass), folded in by Phase 2 — this is why the term cannot
  be in Phase 1.
- Recency is **not** in the score. Recency is already the secondary sort
  key in L1; baking it into importance double-counts it and re-creates
  today's recency bias through the back door.

Weights are constants in one module (`mempalace/importance.py`, new);
tuning is deliberately out of scope for v1 (see Open Questions).

### A.3 Backfill

`mempalace digest --rebuild --wing <wing>` recomputes importance for the
wing's drawers. **The write primitive is `collection.update(ids, metadatas=…)`,
not `upsert`** — two verified reasons:

1. **No re-embedding.** `upsert` with `documents=` hands the text back to
   the embedding model; the base-class `update` (get + merge + upsert)
   and the sqlite_exact override (`sqlite_exact.py:739`) both merge
   metadata onto the **existing stored document and embedding** —
   metadata-only cost. `scripts/backfill_authored_at.py:70` is the
   in-tree precedent using exactly `collection.update(ids, metadatas)`.
2. **Merge, not replace.** `update` merges per-key into existing
   metadata (`base.py` default: `new_meta.update(...)`); a plain
   `upsert(metadatas=…)` would silently drop every key not carried in
   the new dict.

Chunked in batches (the backfill script's pending-list pattern), drawer
ids stable throughout. This honors R6: merge metadata, never touch
`documents` or embeddings.

## §B. Workstream B — Graph-Fed L1

### B.1 The seam

`Layer1.generate()` gains an optional KG section, read via the existing
`KnowledgeGraph` API (`query_entity`, `timeline`) — no schema changes:

```
## L1 — ESSENTIAL STORY
[core]                                    ← new, ≤ 600 chars
  Ben — partner; drives auth work (7 triples, 3 live)
  Meds — active wing since 2026-09; 2 open threads
[rooms]                                   ← digest-driven story (Workstream C)
[general]                                 ← per-drawer fallback (today's behavior)
```

### B.2 Selection rule

Top entities by (live triple count, **last `valid_from`**, name), capped
to the 600-char slice inside the existing `MAX_CHARS = 3200` budget.
Only *live* triples count — `invalidate`/`supersede` history must not
present expired facts as current (this is what `as_of` filtering already
does in `query_entity`).

Timestamp caveat, verified against the schema: triples carry
`valid_from` (when the fact became true), **not** a last-mentioned
timestamp. A entity whose every triple was asserted months ago but is
still true ranks by that old `valid_from`, and there is no cheap "when
was this last talked about" column to sort by. v1 accepts this: ranking
by `valid_from` recency is a defensible proxy for freshness of the
*fact*, and cross-referencing entity mentions against drawer
`filed_at`/`entities` metadata is deferred with the topic-arc work
(Open Questions). If the proxy proves misleading in the L1 quality eval,
the fallback selection rule is pure live-triple count.

### B.3 Degradation

No KG, empty KG, or KG read failure ⇒ section omitted, exactly as L0
omits itself when `identity.txt` is absent. Wake-up never fails because
of the graph.

## §C. Workstream C — The Digest Collection

### C.1 Shape

One digest document per (wing, room) in a new `mempalace_digest`
collection — mirroring `mempalace_closets`:

```
DIGEST wing=projects room=2026-09-15
Discussed drawer id purity; decided content-addressed ids for v4; Ben
flagged migration risk on tunnels.|→drawer_a1,drawer_a2,drawer_b7
Chose snapshot-then-tail for rejoin; test plan owed to windows
machine.|→drawer_c3
```

- Line syntax reuses the closet grammar: `text|→drawer_id,drawer_id`
  (pointer regex `→([\w,]+)` at `searcher/__init__.py:46`; the parse
  helper `_extract_drawer_ids_from_closet` lives at
  `searcher/filters.py:26` — currently exercised only by tests
  (`tests/test_closets.py:506`), so the digest builder becomes its first
  production caller and inherits its tested dedup semantics).
- Size caps: 1,500 chars per digest document (same constant family as
  `CLOSET_CHAR_LIMIT`), rooms exceeding the cap shard like closets.
- Metadata: `wing`, `room`, `built_at`, `drawer_count`, `model` (which
  generator produced it: `extractive` or the local-LLM id).

### C.2 Generation (two tiers, per R5)

1. **Extractive (default, zero LLM).** Compose from existing derived
   artifacts: closet topic lines for the room + first-sentence of the
   highest-importance drawers + entity mentions. No model calls, fully
   deterministic, testable golden-output.
2. **Local-LLM enrichment (opt-in).** Same input bundle, summarized by a
   configured local runtime through the existing `llm_client.py` path —
   the same opt-in posture as closet LLM refinement and `llm_refine.py`.

Both tiers emit pointer lines or are invalid — a digest line without a
`→drawer` reference fails the builder (R1: a digest must always be
traceable to verbatim sources).

### C.3 Lifecycle

- **Build**: `mempalace digest --rebuild [--wing W]`, and opportunistically
  at the end of `mempalace sweep` runs (sweeper cadence already exists;
  the pass is idempotent and resume-safe like the rest of sweep).
- **Purge**: by (wing, room) scope before rebuild — the digest analogue
  of `purge_file_closets`, never a global wipe in one operation.
- **Read**: L1 consumes digests for rooms selected by
  (max drawer importance, recency); explicit read via CLI
  (`mempalace digest --wing W`) and two MCP tools
  (`mempalace_digest_build`, `mempalace_digest_read`), following the
  standard addition recipe in `CLAUDE.md` (handler + `TOOLS` schema).

### C.4 Search isolation (the load-bearing constraint, R2)

- Digests live only in `mempalace_digest`. The searcher's collection set
  is unchanged: `query.py` ranks drawers, closets boost
  (`_closet_boosts`, `searcher/query.py:101`) — digests do neither.
  (Note: closets participate in ranking as a signal only — never a gate
  — per the `_closet_boosts` docstring; the older closet-first
  hydration path formerly described in `docs/CLOSETS.md` no longer
  exists in the code, and that doc is refreshed in the same change to
  describe the boost path.)
- Digest text is never embedded into the drawers or closets collections.
- Rationale: today's hybrid ranking earns 96.6/98.4 R@5 on verbatim text
  only. Summary vocabulary interleaved into ranking is exactly the
  failure mode R2 forbids: the summary's paraphrase shadowing the user's
  original words. If digests ever become searchable, that change ships
  alone, behind an eval proving R2 under adversarial paraphrase queries.

## Constitution Compliance Checklist

| Principle | How this RFC honors it |
|---|---|
| Verbatim always | Digests are views; pointers mandatory; drawers untouched |
| Incremental only | Backfill merges metadata in place; digest purge is scoped to the derived collection |
| Entity-first | KG feeds L1; entity density feeds importance |
| Local-first, no external API | Extractive default; LLM tier is local runtime or explicit BYOK |
| Performance budgets | Nothing new in hooks; wake-up reads precomputed digests |
| Privacy by architecture | No new egress paths; all artifacts local |
| Background everything | Builds ride sweep/daemon/CLI cadence |

## Alternatives Considered

| Option | Verdict |
|---|---|
| Full three-tier restructure (summary as stored tier) | Rejected — violates Verbatim/100%-recall; duplicates drawers+closets for the fragment tier; summary tier creates a second system of record |
| Summaries as drawers with `is_digest` metadata | Rejected — pollutes the verbatim corpus and the ranking pool; purge/rebuild semantics collide with append-only drawers |
| Do nothing | Rejected — L1 remains "recent 15", KG stays dark; wake-up quality gap is user-visible today |
| External memory product integration | Out of scope — different product shape; no egress allowed anyway |
| **Derived views (this RFC)** | Accepted direction — closes all three gaps with closets-proven machinery, zero constitutional surface |

## Testing & Measurement

- **Golden tests**: extractive digest determinism (same drawers ⇒ byte-
  identical digest); pointer-validity invariant (every line resolves to a
  live drawer id).
- **Regression gate**: LongMemEval raw + hybrid v4 runs before/after must
  match existing committed results (`benchmarks/results_*`) exactly — R2
  as a CI-able assertion.
- **L1 quality eval**: hand-labeled set (~50 wake-ups across dogfood
  wings) scored for "stable-fact presence" (core entities, long-lived
  decisions) vs baseline L1. Target: measurable lift, wake-up tokens
  within the ~600–900 budget.
- **Budget tests**: wake-up under 100 ms with digests present; digest
  build excluded from hook paths (assert by code path review + timing
  test).
- **Metadata-merge regression**: after Phase-2 update and after backfill,
  assert every drawer's pre-existing metadata keys (wing, room,
  source_file, entities, …) are unchanged — guards the update-vs-upsert
  primitive and the R6 merge semantics.

## Rollout

1. A (importance) — smallest, independently valuable; L1 improves the
   moment backfill runs. Ships first.
2. B (graph-fed L1) — additive section; ships behind no flag (degrades
   to omission).
3. C (digests) — config-gated (`"digest": {"enabled": true}` in
   `config.json`, default off), enabled on dogfood palaces, default-on
   after the regression gate holds across one release cycle.

Each step is independently shippable and revertible (delete the derived
artifacts; nothing else references them).

## Open Questions

- Importance decay: should `importance` erode with content age, or does
  L1's recency secondary key suffice? (v1: secondary key suffices.)
- Digest granularity beyond rooms: cross-room "topic arcs" (a decision
  evolving over weeks) — valuable but requires the graph; defer. This is
  also the natural home for the deferred "entity last-mentioned" signal
  (§B.2 caveat).
- Local-LLM tier default: enable automatically when an Ollama-class
  runtime is detected, or always require opt-in? (Lean: opt-in, matching
  closet LLM posture.)
- Searchable digests (deferred, §C.4) — what eval would suffice?
- Interaction with RFC 004 step 2a: confirm digest rebuild subscribes to
  op-log fold events rather than wall-clock sweep when the op-log lands.
- Backends without `update` overrides fall back to the base class's
  get + merge + upsert — correct but not atomic. Does the Phase-2
  closet-time importance fold need a capability token
  (`supports_update`) for atomicity, or is the in-lock execution
  (inside `mine_lock`) sufficient? (Lean: mine_lock suffices; the
  authored_at backfill already lives with the same property.)
