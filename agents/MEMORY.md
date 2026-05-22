# Agent Memory

**Workspace:** tx10-odoo | **Branch:** 19.0 | **Last updated:** 2026-05-22

Purpose: Root causes of errors, actions tried, what succeeded, positive and negative learnings per phase.

---

## Phase 1 — Context Detection

**What succeeded:**
- Plugin mode detected via context string, not filesystem inspection
- State file (`agents/init-workspace-flow-state.md`) created successfully on first write
- Mode = `plugin` correctly determined: running as a plugin embedded in a larger context, not as a standalone workspace manager

**Learnings:**
- Plugin mode skips Phases 2 (shells) and 4 (rules) — these are only relevant in direct workspace mode
- File inventory scan revealed 12 expected files missing at project start — normal for a fresh workspace init

---

## Phase 3 — Discovery (Tech Stack, Code Map, Dependencies)

**What succeeded:**
- File count estimated from directory tree analysis: ~21,000 total (14,298 Python + 5,000+ XML + 2,000+ JS/CSS)
- Tech stack fully recovered from 5 source files: `setup.py`, `requirements.txt`, `odoo/release.py`, `ruff.toml`, `setup.cfg`
- Version bounds extracted directly from `release.py` constants (`MIN_PY_VERSION`, `MAX_PY_VERSION`, `MIN_PG_VERSION`)
- TECHSTACK.md, CODEMAP.md, DEPENDENCIES.md created without errors

**Learnings:**
- `odoo/release.py` is the canonical source for version constraints — more reliable than README badges
- `setup.py` `install_requires` and `extras_require` map cleanly to dependency categories (data processing, crypto, imaging, etc.)
- Windows support is a genuine exception path — gevent absent, pypiwin32 substituted
- `requirements.txt` has 103 entries with pinned versions; treat as ground truth for exact versions

**Negative learnings:**
- Do not infer Python version from `setup.cfg` `[flake8]` section — it only controls linting, not runtime

---

## Phase 5 — Pattern Extraction

**What succeeded:**
- ORM patterns extracted from `odoo/orm/` (models.py, fields.py, fields_relational.py, domains.py) and validated against real usage in `addons/account/`
- All 11 pattern files created with syntax-validated code examples
- Mixin composition patterns (mail.thread, portal.mixin) documented inline within `orm-model-pattern.md` rather than as a separate file — kept pattern count manageable
- `wizard-transient-model-pattern.md` synthesized from `odoo/orm/models_transient.py` + `addons/account/wizard/` structure without reading every wizard file directly — structurally accurate
- OWL component pattern (`owl-component-pattern.md`) extracted from `addons/board/static/src/board_controller.js` and `addons/mrp_subcontracting/static/src/components/` — representative sample

**Known gaps (carry to Phase 7):**
- `search-view-pattern.md` not extracted: search views use a distinct XML structure (`<search>`, `<filter>`, `<group by>`) that warrants its own pattern; deprioritized to stay within Phase 5 scope
- OWL XML template pairing inferred from directory structure — `.js` component and `.xml` template are co-located but the template-to-component binding mechanism was not read from source
- Mixin composition not extracted as a standalone pattern — inline in orm-model-pattern; may be promoted in Phase 7 if user requests it

**Negative learnings:**
- Reading every wizard file individually is not necessary — the `TransientModel` pattern is uniform; sampling 2-3 examples is sufficient
- Do not add patterns for every unique variation — prefer one canonical example with callout notes for variants

---

## Phase 6 — Documentation

**What succeeded:**
- All 5 documentation files created: CONTEXT.md, ARCHITECTURE.md, ASSUMPTIONS.md, IMPLEMENTATION.md, MEMORY.md
- Cross-references between files consistent (CONTEXT → README + TECHSTACK; ARCHITECTURE → TECHSTACK + PATTERNS + CODEMAP; ASSUMPTIONS → TECHSTACK + DEPENDENCIES + ARCHITECTURE)
- Architecture file structured as progressive disclosure: system boundary diagram → layer-by-layer detail → patterns reference
- Assumptions file separated into three categories (known, unknowns, constraints) for clarity

**Learnings:**
- CONTEXT.md should contain zero technical implementation details — business purpose and community governance only
- ARCHITECTURE.md is the right place for all code structure, ORM mechanics, HTTP routing, security model, and testing strategy
- ASSUMPTIONS.md is most useful when unknowns include a "why it matters" column — forces prioritization
- IMPLEMENTATION.md + MEMORY.md are agent-internal files; keep them factual and concise, not narrative

**Positive patterns established:**
- Every doc file includes a header row: workspace name, branch, last-updated date
- Every doc file ends with a "Related Documentation" section linking to sibling files
- Tables preferred over prose lists for structured information (version matrices, file inventories, gap tracking)

---

## File Count Reference

| Type | Count | Source |
|------|-------|--------|
| Python (.py) | ~14,298 | Phase 3 directory tree |
| XML (.xml) | ~5,000+ | Phase 3 directory tree |
| JS/CSS | ~2,000+ | Phase 3 directory tree |
| Total | ~21,000+ | Phase 3 directory tree |
| Community addons | 622 | Phase 3 `addons/` directory |
| Built-in addons | 24 | Phase 3 `odoo/addons/` directory |
| ORM sub-modules | 25 | Phase 3 `odoo/orm/` directory |
| CLI subcommands | 20 | Phase 3 `odoo/cli/` directory |
| Tool utilities | 49 | Phase 3 `odoo/tools/` directory |
| Patterns extracted | 11 | Phase 5 |

---

## Phase 7 — HITL User Context Clarification

**What succeeded:**
- User context obtained and analyzed: deployment stage, business module status, CI/CD status, research goal
- Research goal identified: AI-first CRM/ERP system design and implementation
- High-priority research gaps documented in ASSUMPTIONS.md

**User answers (2026-05-22):**
| Question | Answer |
|----------|--------|
| Deployment context | Learning/research + Development/testing (NOT production) |
| Business modules configured | None yet (fresh clone) |
| CI/CD pipeline | None yet (not needed in research phase) |
| Critical research direction | "How can Odoo become an AI-first CRM/ERP system?" |

**Key learnings:**
- This is NOT a production system — research/experimentation is encouraged
- Focus shifts from module configuration to AI integration patterns
- High-priority unknowns now: LLM API injection points, AI field computation, workflow automation with AI
- Documentation should evolve to support AI-integration reference patterns

**Gaps identified for Phase 5+ follow-up:**
- AI-specific pattern library (not yet extracted in Phase 5)
  - LLM prompt engineering patterns for Odoo context
  - Async API call patterns (Claude, GPT APIs in compute functions)
  - Mixin patterns for AI field types
  - Controller/view integration with LLM outputs
- Candidate for new pattern doc: `docs/PATTERNS/ai-integration-pattern.md`

**Action items:**
- Update CONTEXT.md with "Research Focus" section (Phase 7)
- Add AI-integration patterns to Phase 5+ backlog
- Document findings in IMPLEMENTATION.md for next session

---

## Phase 8 — GitNexus Installation & Indexing (2026-05-22)

**What succeeded:**
- GitNexus CLI installed and operational (`v1.x`, npm installed via nvm)
- `gitnexus analyze .` completed successfully against full 19.0 codebase
- Index created at `.gitnexus/` with SQLite database (lbug.wal, lbug)
- Repository automatically registered in global GitNexus registry

**Index Statistics (42,971 files analyzed):**
- Files: 42,971 (includes Python, XML, JS, CSS, PO, PNG, PDF, data files)
- Symbols: 286,961 (largest of all indexed projects!)
- Edges: 591,148 (relationships between symbols)
- Clusters: 6,117 (functional areas)
- Processes: 300 (execution flows)
- Indexed timestamp: 5/22/2026, 4:14:45 PM (commit f399f99)
- Status: ✅ up-to-date

**Learnings:**
- Odoo is an extremely complex codebase — 286K symbols is 27x larger than next-tx10 (1.1K) and 16x larger than agents-tx10 (18.5K)
- Translation files (.po) are excluded from analysis (correctly)
- GitNexus handles large codebases efficiently — analysis completed in ~10 minutes with 8GB RAM allocation
- Symbol extraction accuracy appears high — 591K edges for 287K symbols = ~2.06 edges/symbol (reasonable for Python ORM code)

**Available tools post-installation:**
- `gitnexus query {query: "concept"}` — semantic search for execution flows
- `gitnexus context {name: "symbol"}` — 360-degree view of any symbol
- `gitnexus impact {target: "symbol"}` — blast radius analysis
- MCP gitnexus server accessible for use in code navigation

**Next steps (Phase 9):**
- Verify index accessibility via gitnexus MCP server
- Document gain.json creation requirements
- Final verification of workspace setup

---

## Pending (Phase 9+)

| Item | Priority | Dependency |
|------|----------|------------|
| AI-integration reference patterns | High | Phase 5+ follow-up (next session) |
| search-view-pattern.md | Medium | User request (next session) |
| gain.json creation | Low | Phase 9 only |
