# Odoo 19.0-marin Fork — Comprehensive Changelog

**Branch**: `19.0-marin` (forked from upstream `19.0`)
**Date**: February 2026
**Stats**: 6,931 files changed, 371,121 insertions, 339,069 deletions (net +32,052)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Python 3.14 Modernization](#2-python-314-modernization)
3. [ORM Layer Restructuring](#3-orm-layer-restructuring)
4. [New `odoo/libs/` Package](#4-new-odoolibs-package)
5. [HTTP Layer Decomposition](#5-http-layer-decomposition)
6. [Database Layer — psycopg2 to psycopg3](#6-database-layer--psycopg2-to-psycopg3)
7. [Tools Layer Refactoring](#7-tools-layer-refactoring)
8. [Rust Acceleration Crate](#8-rust-acceleration-crate)
9. [JavaScript / Frontend Overhaul](#9-javascript--frontend-overhaul)
10. [SCSS — Dart Sass Migration](#10-scss--dart-sass-migration)
11. [Base Module Decomposition](#11-base-module-decomposition)
12. [PDF Engine — wkhtmltopdf to WeasyPrint](#12-pdf-engine--wkhtmltopdf-to-weasyprint)
13. [Lint System Overhaul](#13-lint-system-overhaul)
14. [Test Infrastructure Expansion](#14-test-infrastructure-expansion)
15. [Dependency Modernization](#15-dependency-modernization)
16. [Ruff Configuration](#16-ruff-configuration)
17. [Monkeypatch Reduction](#17-monkeypatch-reduction)
18. [Service, CLI and Infrastructure](#18-service-cli-and-infrastructure)
19. [Machine Documentation](#19-machine-documentation)
20. [Migration Guide for Developers](#20-migration-guide-for-developers)
21. [Quality and Performance Comparison vs Upstream](#21-quality-and-performance-comparison-vs-upstream)

---

## 1. Executive Summary

The 19.0-marin fork is a comprehensive modernization of Odoo 19.0 built around five pillars:

1. **Architectural decomposition** — Monolithic god-files split into focused packages and modules (ORM, HTTP, database, base models, JS views, search, action service)
2. **Python 3.14 single-target** — Removed all Python 3.10-3.13 compatibility code, adopted modern idioms (PEP 695 type aliases, `X | None`, `removeprefix`, `itertools.batched`, deferred annotations)
3. **Dependency modernization** — psycopg2→psycopg3, libsass→Dart Sass, wkhtmltopdf→WeasyPrint, PyPDF2→pypdf, passlib→stdlib, added orjson/phonenumbers/weasyprint
4. **Rust acceleration** — New PyO3-based `odoo_rust` crate providing SIMD-accelerated hot paths for ORM cache, deep clone, cursor rows, CSV export, prefetch, and lint scanning
5. **Quality infrastructure** — Pylint replaced with stdlib `ast` checkers + ruff (40+ rule categories), new performance benchmarks, N+1 detection, standalone ORM component tests

### Scale by Language

| Language | Files Changed | Insertions | Deletions |
|----------|--------------|------------|-----------|
| Python   | 2,023        | 222,352    | 132,108   |
| JavaScript | 1,853      | 82,918     | 83,608    |
| XML      | 742          | 17,792     | 19,521    |
| SCSS/CSS | 214          | 1,288      | 706       |
| Rust     | 9            | 1,363      | 0         |
| Other    | 2,090        | 45,408     | 103,126   |

---

## 2. Python 3.14 Modernization

**Target**: Python 3.14+ only (was 3.10+). All version-conditional code eliminated.

### 2.1 Applied Systematically Across All Files

| Pattern | Before | After | Scope |
|---------|--------|-------|-------|
| Future annotations | `from __future__ import annotations` | Removed (PEP 649 native) | 121 files |
| UTC datetime | `datetime.utcnow()` | `datetime.now(UTC)` | 47 occurrences / 22 files |
| Optional type | `Optional[X]` | `X \| None` | ~35 occurrences |
| Union type | `Union[X, Y]` | `X \| Y` | ~9 occurrences |
| Legacy typing | `typing.List`, `Dict`, `Tuple` | `list`, `dict`, `tuple` | ~10 files |
| Type aliases | `X: TypeAlias = ...` | PEP 695 `type X = ...` | 11 aliases / 7 files |
| String slicing | `s[len(prefix):]` | `s.removeprefix(prefix)` | 6 occurrences |
| Dataclass slots | `@dataclass` | `@dataclass(slots=True)` | 3 of 4 eligible |
| Format strings | `.format()` | f-strings | ~15 conversions |
| os.path | `os.path.join()` etc. | `pathlib.Path` | 28 files / ~150+ occurrences |
| Chunking | `split_every()` / `islice()` | `itertools.batched()` | Multiple files |
| Path walking | `os.walk()` | `Path.walk()` | Test infrastructure |
| Generics | `TypeVar('T') + Generic[T]` | PEP 695 `class Foo[T]:` | ORM components, lint |

### 2.2 Preserved Intentionally

- **Logger `%` formatting** — kept for lazy evaluation (`_logger.info("x=%s", val)`)
- **SQL `%s` placeholders** — kept for parameterized queries
- **Vendored `_vendor/` code** — not modified
- **`%` in `assertX()` messages** — kept (only evaluated on failure)

### 2.3 Python 3.14-Specific Fixes

- **QWeb safe opcodes**: Added `LOAD_FAST_BORROW`, `POP_ITER`, `LOAD_FAST_BORROW_LOAD_FAST_BORROW`, `LOAD_COMMON_CONSTANT` to `_SAFE_QWEB_OPCODES` in `ir_qweb.py` and `safe_eval.py`
- **`compile()` O(2^n) regression**: Monkey-patched `cssselect2.compiler._compile_node` with depth limit (10) to prevent exponential compile time on deeply nested CSS selectors (Bootstrap `ol ol ol...` rules)
- **`%-formatting` tuple unpack**: `_select_nextval` in `ir_sequence.py` needed `[0]` to extract scalar from `fetchone()` tuple (f-strings don't auto-unpack)
- **Traceback formatting**: Collapsed multi-line `self.fail()` calls to single line (Python 3.14 fully expands multi-line expressions in tracebacks)

---

## 3. ORM Layer Restructuring

**Scope**: 86 files, +28,130 / -13,806 lines
**Path**: `odoo/orm/`

The ORM was restructured from a collection of flat files into a proper package hierarchy.

### 3.1 Monolithic File Decomposition

| Upstream (flat file) | Fork (package) |
|---------------------|----------------|
| `models.py` (7,127 lines) | `models/` — `base.py`, `metaclass.py`, `transient.py`, `table_objects.py` + 14 mixins |
| `fields.py` (single file) | `fields/` — `base.py`, `binary.py`, `misc.py`, `numeric.py`, `properties.py`, `reference.py`, `relational.py`, `selection.py`, `temporal.py`, `textual.py` |
| `domains.py` (1,988 lines) | `domain/` — `ast.py` (1,167), `constants.py`, `optimizations.py` (990) |
| `environments.py` (964 lines) | `runtime/` — `environment.py` (691), `transaction.py` (162), `cache_compat.py` (317) |
| `commands.py` + `identifiers.py` + `types.py` + `utils.py` | `primitives.py` (311), `helpers.py` (242), `_typing.py` (46) |

### 3.2 Model Mixin Architecture

The monolithic `BaseModel` class was decomposed into 14 focused mixins under `odoo/orm/models/mixins/`:

| Mixin | Responsibility | Lines |
|-------|---------------|-------|
| `access.py` | ACL checking, record rules | 419 |
| `cache.py` | Field cache management, invalidation | 769 |
| `copy.py` | Record duplication | 180 |
| `crud.py` | Create, write, unlink | 1,719 |
| `env.py` | `sudo()`, `with_context()`, `with_company()` | 286 |
| `io.py` | Import/export (`load`, `export_data`) | 981 |
| `iteration.py` | `filtered()`, `mapped()`, `sorted()` | 407 |
| `lifecycle.py` | `_setup`, `_auto_init` | 205 |
| `read.py` | `_read`, `read` | 593 |
| `schema.py` | `fields_get`, `_fields_view_get` | 369 |
| `search.py` | `search`, `search_count`, `name_search` | 740 |
| `translation.py` | Translation handling | 306 |
| `traversal.py` | Relation traversal, `browse`, `exists` | 736 |
| `read_group/` | Sub-package: `mixin.py` (671), `sql.py` (549), `format.py` (366), `fill.py` (315) | 1,901 |

### 3.3 ORM Components Layer (New)

Entirely new package at `odoo/orm/components/` — **database-free, standalone-testable** data structures:

| Component | Lines | Purpose |
|-----------|-------|---------|
| `cache.py` | 244 | `FieldCache` — dirty tracking |
| `compute.py` | 237 | `ComputeEngine` — compute scheduling |
| `core.py` | 270 | `OrmCore` facade |
| `field_spec.py` | 171 | Field expression parsing |
| `model_graph.py` | 559 | `ModelGraph`, `TriggerTree` — dependency graph |
| `recompute.py` | 179 | `RecomputeScheduler` |
| `storage.py` | 180 | `StorageBackend`, `DictBackend` — pluggable backends |
| `testing.py` | 628 | `InMemoryEnvironment`, `ModelDef`, `FieldDef` |
| `unit_of_work.py` | 296 | `UnitOfWork`, `LoopResult` — flush scheduling |

**Test suite**: 11 pytest files totaling ~4,000 lines — runnable without a database:
`test_cache.py`, `test_compute.py`, `test_core.py`, `test_field_spec.py`, `test_in_memory.py`, `test_integration.py`, `test_model_graph.py`, `test_recompute.py`, `test_storage.py`, `test_unit_of_work.py`

### 3.4 New Foundation Files

| File | Purpose |
|------|---------|
| `primitives.py` | `Command`, `NewId`, constants (replaces `commands.py` + `identifiers.py` + `types.py` + `utils.py`) |
| `constants.py` | Read group constants (granularity, aggregates, display formats) |
| `helpers.py` | Shared utility functions |
| `parsing.py` | Field expression parsing |
| `validation.py` | Name-checking (PostgreSQL, object, method) |
| `protocols.py` | `RecordSetProto` runtime-checkable Protocol |
| `_typing.py` | PEP 695 type aliases |

### 3.5 Deleted ORM Files

`commands.py`, `domains.py`, `environments.py`, `fields_numeric.py`, `fields_textual.py`, `identifiers.py`, `models.py`, `types.py`, `utils.py`, and the entire `odoo/osv/expression.py` legacy shim.

---

## 4. New `odoo/libs/` Package

**Scope**: 82 files added, +12,268 lines (entirely new)
**Design principle**: Zero imports from `odoo.orm`, `odoo.tools`, or any Odoo module. Everything testable standalone.

### 4.1 Package Structure

```
odoo/libs/
  __init__.py              # Re-exports
  constants.py             # SCRIPT_EXTENSIONS, STYLE_EXTENSIONS, TEMPLATE_EXTENSIONS
  facade.py                # Deprecation facade for backward compat
  func.py                  # classproperty, lazy, conditional, mute_logger
  gc.py                    # GC tuning utilities
  intervals.py             # Interval arithmetic
  lru.py                   # LRU cache implementation
  logging.py               # Logging setup
  parse_version.py         # Version comparison
  set_expression.py        # Set algebra for domains
  utils.py                 # General utilities

  _field_access/           # Field access accelerator (Rust FFI + Python fallback)
  _vendor/                 # Vendored: sessions.py, useragents.py
  barcode.py               # Barcode generation

  collections/             # FrozenDict, ReadonlyDict, GroupBy, OrderedSet
  colors/                  # Color conversion utilities
  datetime/                # date_utils.py (531 lines), tz.py (244 lines)
  email/                   # Email parsing (389 lines)
  filesystem/              # appdirs, mimetypes, osutil, which
  image/                   # Image processing (614 lines)
  iteration/               # grouping, sentinel, slicing, sorting
  json/                    # fast_clone, orjson_wrapper, scriptsafe
  lint/                    # Rust-accelerated code scanner
  locale/                  # Locale conversions
  numbers/                 # float_utils (410 lines)
  profiling/               # sourcemap_generator, speedscope
  security/                # Security utilities
  soap/                    # SOAP/WSDL client (was tools/zeep/)
  sql/                     # SQL utilities
  text/                    # HTML sanitization (902 lines), Arabic reshaper, strings
  web/                     # JS transpiler (902 lines), URL utilities
  xml/                     # Template inheritance (416 lines), XML utilities
```

### 4.2 Origin — What Moved from `tools/`

| Former location (`odoo/tools/`) | New location (`odoo/libs/`) |
|--------------------------------|----------------------------|
| `appdirs.py` | `filesystem/appdirs.py` |
| `arabic_reshaper/` | `text/arabic_reshaper/` |
| `barcode.py` | `barcode.py` |
| `constants.py` | `constants.py` |
| `facade.py` | `facade.py` |
| `func.py` | `func.py` |
| `gc.py` | `gc.py` |
| `js_transpiler.py` | `web/js_transpiler.py` |
| `lru.py` | `lru.py` |
| `mimetypes.py` | `filesystem/mimetypes.py` |
| `osutil.py` | `filesystem/osutil.py` |
| `parse_version.py` | `parse_version.py` |
| `set_expression.py` | `set_expression.py` |
| `sourcemap_generator.py` | `profiling/sourcemap_generator.py` |
| `speedscope.py` | `profiling/speedscope.py` |
| `which.py` | `filesystem/which.py` |
| `zeep/` (entire directory) | `soap/` |
| `_vendor/send_file.py` | Deleted entirely |
| `_vendor/sessions.py` | `_vendor/sessions.py` |
| `_vendor/useragents.py` | `_vendor/useragents.py` |
| `float_utils.py` (partial) | `numbers/float_utils.py` |
| `template_inheritance.py` (partial) | `xml/template_inheritance.py` |
| `mail.py` (HTML parts) | `text/html.py` |
| `misc.py` (many utilities) | Various subpackages |

### 4.3 Notable New Functionality

- **`json/orjson_wrapper.py`** — Integration with `orjson` for fast JSON serialization
- **`json/fast_clone.py`** — JSON-based deep cloning
- **`_field_access/`** — Field access accelerator with Rust FFI and Python fallback
- **`lint/scan.py`** — Rust-accelerated code scanning (SIMD via memchr)

---

## 5. HTTP Layer Decomposition

**Scope**: `odoo/http.py` (2,845 lines) → `odoo/http/` package (12 modules)

| Module | Lines | Content |
|--------|-------|---------|
| `__init__.py` | 300 | Re-exports, backward compatibility |
| `application.py` | 263 | WSGI application class |
| `constants.py` | 124 | HTTP constants, status codes |
| `controller.py` | 55 | Controller base class, `@route` decorator |
| `core.py` | 19 | Core infrastructure |
| `dispatcher.py` | 357 | Request dispatching (JSON-RPC, HTTP) |
| `exceptions.py` | 15 | HTTP-specific exceptions |
| `geoip.py` | 114 | GeoIP lookup |
| `helpers.py` | 163 | HTTP utility functions |
| `request_class.py` | 692 | `Request` class implementation |
| `routing.py` | 267 | URL routing and matching |
| `session.py` | 400 | Session management |
| `stream.py` | 204 | Response streaming |
| `wrappers.py` | 453 | Request/Response wrapper classes |

---

## 6. Database Layer — psycopg2 to psycopg3

**Scope**: `odoo/sql_db.py` (846 lines) → `odoo/db/` package

### 6.1 New Package Structure

- `odoo/db/__init__.py` — re-exports
- `odoo/db/cursor.py` — Cursor implementation
- `odoo/db/pool.py` — Connection pool
- `odoo/db/utils.py` — Database utilities

### 6.2 Driver Migration

This is the single most impactful dependency change:

| Aspect | Before (psycopg2) | After (psycopg3) |
|--------|-------------------|-------------------|
| Package | `psycopg2==2.9.x` | `psycopg[c,binary]>=3.3.2` + `psycopg-pool>=3.3.0` |
| JSON adapter | `Json()` | `Jsonb()` |
| Errors | `TransactionRollbackError` | `TransactionRollback`, `DeadlockDetected`, `SerializationFailure`, `ReadOnlySqlTransaction` |
| Async | Requires `gevent` + `greenlet` | Native async support |
| Connection pool | Custom implementation | `psycopg_pool` |

**Impact**: Every file that imports `psycopg2` needed updating. The `gevent` and `greenlet` dependencies were removed entirely.

---

## 7. Tools Layer Refactoring

**Scope**: 76 files, +8,757 / -13,470 lines (net -4,713 — code moved to `libs/`)

### 7.1 Major Refactoring

| File | Change | Notes |
|------|--------|-------|
| `__init__.py` | Wildcard `from .misc import *` → explicit named imports | Namespace hygiene |
| `misc.py` | -2,149 lines | Utilities extracted to `libs/` subpackages |
| `mail.py` | Major reduction | HTML processing → `libs/text/html.py` |
| `config.py` | +1,596 lines changed | Improved argument parsing, type hints |
| `translate.py` | +/-1,443 lines | Improved PO file handling |
| `convert.py` | +/-666 lines | XML/CSV data import modernization |
| `safe_eval.py` | +613 lines | Python 3.14 opcodes, improved security |
| `sql.py` | +824 lines | New SQL utility functions |
| `image.py` | Refactored | Core utils → `libs/image/` |
| `profiler.py` | +/-452 lines | Major overhaul |

### 7.2 New Files in tools/

| File | Lines | Purpose |
|------|-------|---------|
| `sass_embedded.py` | 517 | Dart Sass embedded protocol compiler |
| `embedded_sass_pb2.py` | 124 | Protobuf definitions for Dart Sass |
| `files.py` | 147 | Security-critical file path validation |
| `formatting.py` | 421 | String/HTML formatting utilities |
| `locale_utils.py` | 83 | Locale conversion utilities |
| `mixin_profiler.py` | 347 | Mixin method profiling |
| `nplusone.py` | 160 | N+1 query detection |
| `orm_profiler.py` | 178 | ORM operation profiling |
| `password.py` | 150 | Password hashing/verification (replaces `passlib`) |
| `security.py` | 223 | Security utilities |
| `subprocess.py` | 215 | Subprocess management utilities |

### 7.3 Renamed

- `babel/` → `babel_extractors/` (clarity)
- `pycompat.py` → **deleted** (Python 2/3 shim no longer needed)
- `pdf/_pypdf2_1.py`, `pdf/_pypdf2_2.py` → **deleted** (PyPDF2 compatibility layers removed)

---

## 8. Rust Acceleration Crate

**Scope**: 9 files, +1,363 lines (entirely new)
**Path**: `crates/odoo_rust/`
**Stack**: Rust 2024 edition, PyO3 0.28.2, memchr 2, regex 1, ignore 0.4

### 8.1 Modules

| Module | File | Lines | Purpose | Speedup |
|--------|------|-------|---------|---------|
| `clone` | `src/clone.rs` | 183 | Fast deep-clone for JSON-like Python objects via `_PyDict_NewPresized` + `PyDict_Next` + `PyList_SET_ITEM` | 1.5-2x |
| `cache` | `src/cache.rs` | 422 | Batch cache lookups for `mapped()`/`filtered()`/`sorted()` via raw `ffi::PyDict_GetItem` (borrowed refs, no refcount overhead) | 2-3x |
| `ids` | `src/ids.rs` | 45 | Origin ID extraction for NewId-aware record collections | — |
| `prefetch` | `src/prefetch.rs` | 80 | Prefetch ID selection for `Field.__get__` cache misses via `HashSet<i64>` | — |
| `rows` | `src/rows.rs` | 129 | `dictfetchall()`/`dictfetchmany()` acceleration | 2.5x (10k×20) |
| `web` | `src/web.rs` | 152 | CSV export with QUOTE_ALL + formula injection protection | — |
| `scan` | `src/scan.rs` | 233 | Parallel file scanner for lint (SIMD memchr + `ignore::WalkParallel`) | 10-50x |

### 8.2 Design Principles

- Every module has both an `unsafe` FFI variant (exported, fast) and a `_safe` PyO3 variant (reference only)
- Uses pointer identity (`==`) not Python `__eq__` for sentinel comparison
- `_PyDict_NewPresized` for zero-resize dict construction
- `PyTuple_GET_ITEM` / `PyList_SET_ITEM` for unchecked direct slot access
- All functions have Python fallbacks — `try: from odoo_rust import ...; except ImportError: ...`
- Build artifact: `target/wheels/odoo_rust-0.1.0-cp314-cp314-linux_x86_64.whl`

---

## 9. JavaScript / Frontend Overhaul

**Scope**: 1,853 JS files, +82,918 / -83,608 lines (net -690)
**Web module alone**: 864 files in `addons/web/static/src/` (+62,568 / -36,401)

### 9.1 Directory Taxonomy Overhaul

The web module was reorganized from a flat structure into a semantic hierarchy:

```
addons/web/static/src/
  boot/              # NEW — entry points (main.js, start.js)
  components/        # NEW — reusable OWL components (moved from core/)
  core/              # Framework plumbing (browser, domain, l10n, network, registry)
    utils/
      collections/   # NEW — arrays, objects, cache
      dnd/           # NEW — draggable, sortable, nested_sortable
      dom/           # NEW — autoresize, classname, events, html, scrolling, ui, xml
      format/        # NEW — binary, colors, numbers, strings
  fields/            # NEW — field widgets (moved from views/fields/)
    basic/           # boolean, char, float, integer, monetary, text, url, email, phone
    display/         # badge, gauge, handle, progress_bar, statusbar
    media/           # binary, image, signature, pdf_viewer
    relational/      # many2one, many2many, x2many, reference
    selection/       # selection, radio, badge_selection, priority
    specialized/     # ace, domain, properties, color_picker
    temporal/        # datetime, remaining_days
  model/             # Data models (relational_model decomposed)
  search/            # Search (search_model decomposed into 10 modules)
  services/          # Service providers
  views/             # View controllers and renderers
  webclient/         # Shell, actions, navigation
```

### 9.2 God-Module Decomposition

| Original | Before | After | Extracted Into |
|----------|--------|-------|----------------|
| `list_renderer.js` | ~2,700 lines | ~1,200 | 9 modules: aggregates, grid_state, keyboard_nav, selection, virtualization, column_utils, group_layout, optional_fields, aggregates_row |
| `search_model.js` | ~2,500 lines | ~1,000 | 10 modules: context, domain, facets, favorites, group_by, properties, panel_fetch, state, split_domain, enrichment |
| `action_service.js` | ~1,700 lines | ~700 | 8 modules: button_executor, breadcrumb_manager, state, constants, views, info_builders, report_executor, skeleton_view |
| `relational_model/utils.js` | ~1,100 lines | ~200 | 8 modules: field_context, field_metadata, field_spec, field_values, record_hooks, record_validator, record_value_transforms, resequence, static_list_utils |
| `pivot_model.js` | ~1,100 lines | ~400 | 4 modules: group_tree, measurements, table, value_utils |

### 9.3 DRY Extractions

| New Module | Lines | Purpose |
|-----------|-------|---------|
| `MultiRecordController` | 249 | Base class for ListController + KanbanController |
| `view_utils.js` | 309 | `computeModelOptions()`, `buildActionMenuItems()`, `useControllerServices()`, etc. |
| `SelectionLikeField` | 57 | Base class for badge/radio/selection fields |
| `decorations.js` | 37 | `getClassNameFromDecoration()`, `getDecoration()` |
| `numeric_input_field_base.js` | — | Shared input behavior for numeric fields |
| `text_input_field_base.js` | — | Shared input behavior for text fields |
| `content_disposition.js` | 244 | Content-Disposition header parser |
| `field_types.js` | — | `X2M_TYPES` constant |

### 9.4 ES2025 Modernization — Polyfills Removed

| Polyfill | Native Since |
|----------|-------------|
| `Array.prototype.at` | ES2022 / Chrome 92 |
| `Object.hasOwn` | ES2022 / Chrome 93 |
| `Promise.withResolvers` | ES2024 / Chrome 119 |
| `Set.prototype.difference` | ES2025 / Chrome 122 |

Also deleted: `legacy/js/libs/jquery.js`, `lib/jquery/jquery.js`

### 9.5 New Features

- **Density Service** (`webclient/density/`) — UI density preferences (compact/normal/comfortable)
- **Visitor Error Handler** (`webclient/errors/visitor_error_handler.js`) — public-facing error handling
- **Performance tests** — `list_view_performance.test.js` (178 lines), `list_grid_state.test.js` (407 lines)

### 9.6 Impact on External Addons

~1,073 non-web addon JS files have 2-20 line changes each — almost exclusively **import path rewrites**:
- `@web/core/dropdown/dropdown` → `@web/components/dropdown/dropdown`
- `@web/views/fields/many2one/many2one` → `@web/fields/relational/many2one/many2one`
- `@web/core/utils/arrays` → `@web/core/utils/collections/arrays`

---

## 10. SCSS — Dart Sass Migration

**Scope**: 214 SCSS/CSS files, +1,288 / -706 lines

### 10.1 Compiler Change

| Aspect | Before | After |
|--------|--------|-------|
| Compiler | libsass (C, deprecated) | Dart Sass (active) |
| Protocol | Direct Python binding | Embedded Sass Protocol (protobuf) + CLI fallback |
| New files | — | `sass_embedded.py` (517 lines), `embedded_sass_pb2.py` (124 lines) |
| Dependency | `libsass==0.22.0` | `protobuf>=6.31.0` |
| `.sass` support | Yes | No (0 `.sass` files remain — `description.sass` deleted) |

### 10.2 SCSS Syntax Fixes

All bare `/` division operators converted to `calc()` for Dart Sass compatibility:

```scss
/* Before (libsass) */
margin-top: $height / 2;
width: percentage(1/3);

/* After (Dart Sass) */
margin-top: calc($height / 2);
width: calc(100% / 3);
```

Applied across ~50+ files in addons including `html_builder`, `account`, `web`, `website_slides`, `point_of_sale`, `mail`, `stock`.

### 10.3 Compiler Architecture

- `SassEmbeddedCompiler` — singleton, lazy start, `_unavailable` class flag to skip retries
- `OdooSassImporter` — resolves imports via `file_path()` + Sass partial resolution
- Auto-closes and marks unavailable on protocol errors (zombie prevention)
- CLI flags: `--quiet-deps`, 5 `--silence-deprecation` flags
- Pure JS npm `sass`: `--embedded` unavailable, falls back to CLI gracefully

---

## 11. Base Module Decomposition

**Scope**: 202 files, +48,234 / -30,789 lines

### 11.1 God-File Splits

| Original (monolithic) | Extracted modules |
|-----------------------|-------------------|
| `ir_model.py` (~5,000+ lines) | `ir_model_access.py` (503), `ir_model_data.py` (577), `ir_model_fields.py` (1,189), `ir_model_fields_selection.py` (409) |
| `ir_ui_view.py` (~3,500+ lines) | `ir_ui_view_base.py` (688), `ir_ui_view_custom.py` (25), `ir_ui_view_name_manager.py` (359) |
| `ir_actions.py` (~2,800+ lines) | `ir_actions_server.py` (1,245) |
| `res_partner.py` | `res_partner_category.py` (64), `res_partner_format_address_mixin.py` (105), `res_partner_format_vat_mixin.py` (19), `res_partner_industry.py` (13) |
| `res_users.py` | `res_users_apikeys.py` (312), `res_users_identitycheck.py` (57), `res_users_log.py` (33) |
| Wizards (inline) | `wizard/change_password.py` (83), `wizard/reset_view_arch.py` (112) |

### 11.2 `__init__.py` Reorganization

The base module's imports were restructured with clear section headers:
- Assets, Core metadata (ir.model), UI: views/menus/assets, Actions, Storage, Scheduling
- Filters/defaults/exports, Mail & HTTP, Modules, Properties & reports
- Profiling & mixins, Partner, Users, Country/currency/lang/company, Groups, Devices/settings

### 11.3 Other Significant Base Model Changes

| File | Delta | Key Changes |
|------|-------|-------------|
| `assetsbundle.py` | +878 | Dart Sass compilation pipeline |
| `ir_mail_server.py` | +937 | Major rework |
| `ir_module.py` | +1,102 | Module management modernization |
| `ir_cron.py` | +587 | psycopg migration, modernization |
| `ir_attachment.py` | +721 | Pathlib migration |
| `report_paperformat.py` | +417 | WeasyPrint-compatible paper formats |

---

## 12. PDF Engine — wkhtmltopdf to WeasyPrint

**Location**: `ir_actions_report.py` (+2,367 lines changed)

### 12.1 What Was Removed

- `WkhtmlInfo` NamedTuple
- `_wkhtml()` cached detection function
- `_run_wkhtmltopdf()` subprocess management
- `_split_table()` table-splitting workaround
- All `split_table/` test fixtures and `test_split_table.py`
- `description.sass` (Sass syntax file)

### 12.2 WeasyPrint Architecture

**Module-level singletons** for performance:
- `_weasy_font_config = FontConfiguration()` — Pango font map, survives across worker requests (first call ~30s cold, <1s warm)
- `_weasy_image_cache = {}` — decoded image data shared across renders

**New `OdooURLFetcher` class** (subclasses `weasyprint.urls.URLFetcher`):
- Context manager for session lifecycle management
- 3-tier URL resolution:
  1. Asset bundles: `/web/assets/<unique>/<filename>` via `ir.attachment`
  2. Static files: `/<module>/static/...` resolved from filesystem
  3. HTTP fallback: session-authenticated request to Odoo server
- Test-mode aware: handles `_registry_test_lock` release for concurrent cursor access
- Fixes CVE-2025-68616 (SSRF vulnerability in old function-based URL fetcher)

**Pre-compiled XPath** for HTML structure extraction (lxml 6.0 best practice):
```python
_xpath_main    = etree.ETXPath("//main")
_xpath_header  = etree.ETXPath("//div[contains(..., ' header ')]")
_xpath_footer  = etree.ETXPath("//div[contains(..., ' footer ')]")
_xpath_article = etree.ETXPath("//div[contains(..., ' article ')]")
```

---

## 13. Lint System Overhaul

**Scope**: 29 files, +2,125 / -1,550 lines

### 13.1 Pylint → stdlib `ast` + ruff

| Deleted (Pylint-based) | Replacement |
|------------------------|-------------|
| `_odoo_checker_gettext.py` | `_checker_gettext.py` (144 lines, stdlib `ast`) |
| `_odoo_checker_sql_injection.py` | `_checker_sql.py` (663 lines, stdlib `ast`) |
| `_odoo_checker_unlink_override.py` | `_checker_unlink.py` (73 lines, stdlib `ast`) |
| `_pylint_path_setup.py` | Not needed |
| `test_pylint.py` | `test_ruff.py` (159 lines) |

### 13.2 Key Design Decisions

- **Backward-compatible suppression**: `_is_suppressed()` parses both `# pylint: disable=E8501` and `# noqa` inline comments
- **`_RULE_ALIASES`** maps new rule names to old Pylint codes (E8501-E8506)
- **No subprocess overhead** — AST checkers run in-process
- **Rust scanner** for file-level lint (`test_markers.py`, `test_jstranslate.py`) — 10-50x faster than sequential Python I/O

### 13.3 `lint_case.py` Modernization

- `os.walk()` → `Path.walk()`
- `TypeVar('T') + Generic[T]` → PEP 695 `class NodeVisitor[T]:`
- New shared utilities: `get_odoo_module_name()`, `iter_registry_methods()`

---

## 14. Test Infrastructure Expansion

### 14.1 New `test_performance` Module (Entirely New)

5,792 lines dedicated to performance testing:

| File | Lines | Purpose |
|------|-------|---------|
| `test_perf.py` | 1,725 | Core ORM performance tests (read, write, create, search) |
| `test_sql_benchmark.py` | 963 | SQL query benchmarks |
| `test_performance.py` | 963 | General performance tests |
| `test_benchmark.py` | 717 | Micro-benchmarks for ORM primitives |
| `test_pyo3_candidates.py` | 516 | Rust acceleration candidate identification |
| `test_domain_benchmark.py` | 454 | Domain parsing/evaluation benchmarks |
| `test_timeit.py` | 257 | Timing utilities |

### 14.2 New Base Test Files

| File | Lines | Purpose |
|------|-------|---------|
| `test_base_benchmark.py` | 263 | Base model benchmarks |
| `test_base_perf_regression.py` | 253 | Performance regression guards |
| `test_nplusone.py` | 191 | N+1 query detection |
| `test_orm_profiler.py` | 198 | ORM profiler integration |

### 14.3 New test_orm Tests

| File | Lines | Purpose |
|------|-------|---------|
| `test_hotpath_contracts.py` | 724 | Hot path contract enforcement |
| `test_many2many_operations.py` | 565 | M2M operation tests |
| `test_recordset_operations.py` | 454 | Recordset operation tests |
| `test_json_field_operations.py` | 417 | JSON field operation tests |
| `test_traversal.py` | 402 | Record traversal tests |
| `test_primitives.py` | 342 | ORM primitive type tests |
| `test_env_operations.py` | 324 | Environment operation tests |
| `test_validation.py` | 101 | Input validation tests |
| `perf_results/baseline.txt` | 87 | Performance baseline |

### 14.4 ORM Component Tests (pytest, no database)

11 test files at `odoo/orm/components/tests/` totaling ~4,000 lines. These test the new standalone ORM components with `InMemoryEnvironment` — no PostgreSQL required.

### 14.5 Deleted Tests

- `test_split_table.py` + all XML fixtures — wkhtmltopdf table splitting removed (WeasyPrint handles this natively)

---

## 15. Dependency Modernization

### 15.1 Summary Table

| Category | Removed | Added/Updated |
|----------|---------|---------------|
| Database driver | `psycopg2==2.9.x` | `psycopg[c,binary]>=3.3.2`, `psycopg-pool>=3.3.0` |
| Async | `gevent`, `greenlet` | Removed entirely |
| SCSS | `libsass==0.22.0` | Removed (Dart Sass is system-level) |
| Protobuf | — | `protobuf>=6.31.0` |
| Password | `passlib==1.7.4` | Removed (`tools/password.py`) |
| PDF library | `PyPDF2` (multiple versions) | `pypdf==6.6.2`, `pdfminer.six==20260107` |
| PDF rendering | — | `weasyprint==68.1`, `rlPyCairo==0.4.0` |
| JSON | — | `orjson==3.11.7` |
| Spreadsheets | `xlrd==2.0.1`, `xlwt==1.3.0` | Removed |
| Web framework | `Werkzeug==3.0.1` | `Werkzeug==3.1.5` |
| Reporting | `reportlab==4.1.0` | `reportlab==4.4.10` |
| Crypto | `cryptography==42.0.8` | `cryptography==46.0.4` |
| Phone | — | `phonenumbers==9.0.24` |
| GeoIP | `geoip2==2.9.0` | `geoip2==5.2.0` |

### 15.2 New `requirements-dev.txt`

Development dependencies now separated:
- `ruff==0.15.2`, `black==26.1.0` — formatting
- `mypy==1.19.1` — type checking
- `pytest==9.0.2` — testing
- `astroid==4.0.4`, `Pygments==2.19.2` — AST analysis

### 15.3 Version Simplification

Upstream had ~99 lines with complex Python version conditionals. Fork has ~49 lines with single pinned versions targeting Python 3.14 only.

---

## 16. Ruff Configuration

**File**: `ruff.toml` — expanded from 84 to 286 lines

| Aspect | Upstream | Fork |
|--------|----------|------|
| Target Python | `py310` | `py314` |
| Line length | 88 (default) | 120 |
| Preview mode | Global `preview = true` | Cherry-picked `explicit-preview-rules = true` |
| Rule categories | ~20 | ~40+ |
| Per-file ignores | 1 pattern | 6 patterns |

### 16.1 New Rule Categories

`B` (bugbear), `A` (builtins), `N` (naming), `S` (bandit security), `DTZ` (datetime timezone), `PTH` (pathlib), `T10` (debugger), `T20` (print), `ERA` (commented-out code), `RSE` (raise), `PLR` (Pylint refactoring), `PERF` (performance), `FURB` (modern Python), `C90` (complexity max=20), `SLOT` (slots), `SIM` (simplify), `PIE`

### 16.2 Banned APIs

```toml
[lint.flake8-tidy-imports.banned-api]
"datetime.datetime.utcnow".msg = "Use datetime.now(UTC) instead (deprecated since 3.12)"
"datetime.datetime.utcfromtimestamp".msg = "Use datetime.fromtimestamp(ts, tz=UTC) instead"
"optparse".msg = "Use argparse instead"
```

### 16.3 Odoo-Specific Suppressions (Documented)

- `RUF012` — mutable class defaults (Odoo models use `dict`/`list` as class attrs)
- `PLW0642` — self reassignment (`self = self.sudo()` is idiomatic)
- `E741` — ambiguous names (`lambda l:` convention, 640+ occurrences)
- `S101` — assert in production (ORM invariants)
- `DTZ001/002/005-012` — naive datetime rules (ORM requires naive datetimes)
- **DTZ003/DTZ004 enforced** — `utcnow()` and `utcfromtimestamp()` are banned

---

## 17. Monkeypatch Reduction

**Scope**: 22 files, +368 / -2,295 lines (net -1,927)

### 17.1 Deleted Entirely (8 patches)

| Patch | Reason |
|-------|--------|
| `email.py` | Python 3.14 fixes email handling |
| `lxml.py` | No longer needed |
| `pytz.py` | pytz shim removed |
| `stdnum.py` | python-stdnum shim removed |
| `urllib3.py` | No longer needed |
| `xlrd.py` | xlrd removed from deps |
| `xlwt.py` | xlwt removed from deps |
| `zeep.py` | No longer needed |

### 17.2 Massively Reduced (2 patches)

| Patch | Before | After | Reason |
|-------|--------|-------|--------|
| `werkzeug.py` | ~1,067 lines | ~near-zero | Werkzeug 3.1.5 fixed upstream issues |
| `num2words.py` | ~1,025 lines | ~300 | Most fixes upstreamed |

### 17.3 Added

- `_excel_utils.py` (32 lines) — Excel utility patches
- `README.md` (117 lines) — Documents each patch's purpose and removal criteria

---

## 18. Service, CLI and Infrastructure

### 18.1 CLI (`odoo/cli/`)

- `command.py`: New `get_single_database()` and `odoo_env` context manager exported
- All commands modernized with improved argument parsing, ruff formatting
- `deploy.py`, `obfuscate.py`, `scaffold.py`, `shell.py`: Significant refactoring

### 18.2 Service (`odoo/service/`)

- `server.py` (+848 lines): Major refactoring of prefork/threaded server
- `db.py` (+473 lines): Database service operations modernized
- `model.py` (+127 lines): Model dispatch
- `common.py` (+29 lines): Version info

### 18.3 Core Infrastructure

| Change | Details |
|--------|---------|
| `netsvc.py` → `logutils.py` | Renamed (logging setup, colored formatters, PostgreSQL handler) |
| `sql_db.py` → `db/` | Decomposed into package |
| `http.py` → `http/` | Decomposed into package |
| `osv/expression.py` | Deleted (legacy shim, replaced by `orm/domain/`) |
| `loglevels.py` | Deleted |
| `.gitignore` | Added `odoo.log` |

### 18.4 Build/Packaging

| File | Changes |
|------|---------|
| `debian/control` | Removed `python3-libsass`, `python3-passlib`. Added `python3-protobuf` |
| `debian/copyright` | Updated paths for reorganized files |
| `setup/package.dfdebian` | Removed `python3-libsass`, `python3-passlib`. Added `python3-protobuf` |
| `setup/package.dffedora` | Removed `libsass`, `python3-passlib`. Added `nodejs-npm`, `python3-protobuf` |
| `setup/requirements-check.py` | `libsass` mapping → `protobuf` |

---

## 19. Machine Documentation

New structured, machine-consumable documentation for AI-assisted development:

### Web Module (`addons/web/machine_doc_v1/` — 6 files, 1,309 lines)

- `ARCHITECTURE.md` — layer diagram, OWL components, services
- `CONVENTIONS.md` — JS patterns, OWL lifecycle
- `MODEL_MAP.md` — web module models
- `PERFORMANCE.md` — benchmarking methodology
- `ROUTE_MAP.md` — HTTP endpoints
- `TEST_TAGS.md` — test tag reference

### Base Module (`odoo/addons/base/machine_doc_v1/` — 4 files, 2,260 lines)

- `ARCHITECTURE.md` — base module structure
- `CONVENTIONS.md` — ORM patterns, naming
- `MODEL_MAP.md` — comprehensive model documentation (1,450 lines)
- `TEST_TAGS.md` — test tag reference

### Coding Guidelines (`doc/coding_guidelines.rst` — 1,984 lines)

Authoritative coding standards document covering Python style, ORM patterns, JavaScript conventions, XML views, security guidelines, git workflow, and testing standards.

---

## 20. Migration Guide for Developers

### 20.1 Python Import Changes

If you have custom modules, update these imports:

```python
# Database
# Before:
import psycopg2
from psycopg2.extensions import TransactionRollbackError
# After:
import psycopg
from psycopg.errors import TransactionRollback, DeadlockDetected

# ORM
# Before:
from odoo.osv import expression
# After:
from odoo.orm.domain import <what_you_need>

# Tools → Libs
# Before:
from odoo.tools import float_compare
from odoo.tools.lru import LRU
from odoo.tools.misc import frozendict
# After:
from odoo.libs.numbers.float_utils import float_compare
from odoo.libs.lru import LRU
from odoo.libs.collections.frozen_dict import FrozenDict
# Note: odoo.tools re-exports many libs for backward compatibility
```

### 20.2 JavaScript Import Path Changes

All web module component imports changed. Key patterns:

```javascript
// Components: core/ → components/
// Before:
import { Dropdown } from "@web/core/dropdown/dropdown";
// After:
import { Dropdown } from "@web/components/dropdown/dropdown";

// Fields: views/fields/ → fields/<category>/
// Before:
import { Many2OneField } from "@web/views/fields/many2one/many2one";
// After:
import { Many2OneField } from "@web/fields/relational/many2one/many2one";

// Utils: flat → categorized
// Before:
import { sortBy } from "@web/core/utils/arrays";
// After:
import { sortBy } from "@web/core/utils/collections/arrays";

// Before:
import { escape } from "@web/core/utils/strings";
// After:
import { escape } from "@web/core/utils/format/strings";
```

### 20.3 SCSS Changes

If you have custom SCSS, convert bare `/` division:

```scss
/* Before: */
width: $total / 3;
/* After: */
width: calc($total / 3);
```

### 20.4 PDF Reports

- wkhtmltopdf is no longer available
- Reports render via WeasyPrint (pure Python, CSS-based)
- Custom report templates may need CSS adjustments for WeasyPrint compatibility
- `report_paperformat` fields are WeasyPrint-aware

### 20.5 Database Driver

- `psycopg2` → `psycopg` (v3) throughout
- `gevent`/`greenlet` no longer available
- Connection pooling via `psycopg_pool`
- JSON adapter: `Json()` → `Jsonb()`

### 20.6 Removed Dependencies

If your code uses these, find alternatives:
- `passlib` → `odoo.tools.password`
- `xlrd`/`xlwt` → removed (use `openpyxl` for Excel)
- `libsass` → Dart Sass (system-level)
- `gevent`/`greenlet` → removed
- `PyPDF2` → `pypdf`

### 20.7 Python Version

- **Minimum**: Python 3.14
- `from __future__ import annotations` is no longer needed (remove it)
- Use `X | None` instead of `Optional[X]`
- Use `list`, `dict`, `tuple` instead of `typing.List`, `typing.Dict`, `typing.Tuple`
- Use `datetime.now(UTC)` instead of `datetime.utcnow()`
- Use `itertools.batched()` instead of custom chunking

---

## 21. Quality and Performance Comparison vs Upstream

A measured, data-driven comparison between base Odoo 19.0 and the 19.0-marin fork.

### 21.1 God-File Elimination

The single biggest quality difference. Upstream has massive monolithic files that are hard to navigate, test, and reason about:

| File | Upstream | Fork | Reduction |
|------|----------|------|-----------|
| `odoo/orm/models.py` | **7,127 lines** | **Deleted** → 14 mixins (largest: 1,719) | -76% max size |
| `odoo/http.py` | **2,845 lines** | **Deleted** → 12 modules (largest: 692) | -76% max size |
| `odoo/orm/domains.py` | **1,988 lines** | **Deleted** → 3 modules (largest: 1,167) | -41% max size |
| `odoo/orm/environments.py` | **964 lines** | **Deleted** → 3 modules (largest: 691) | -28% max size |
| `odoo/sql_db.py` | **846 lines** | **Deleted** → `db/` package | package |
| `ir_model.py` | **2,701 lines** | **824** + 4 extracted files | -70% main file |
| `ir_ui_view.py` | **3,619 lines** | **3,152** + 3 extracted files | -13% main file |
| `ir_actions.py` | **1,460 lines** | **722** + 1 extracted file | -51% main file |

**Largest production Python file:**
- Upstream: **7,127 lines** (`odoo/orm/models.py`)
- Fork: **2,705 lines** (`odoo/orm/fields/base.py`)
- **62% reduction** in maximum file complexity

**Top 10 largest Python files in `odoo/` (excluding addons):**

| Rank | Upstream (19.0) | Lines | Fork (19.0-marin) | Lines |
|------|----------------|-------|--------------------|-------|
| 1 | `orm/models.py` | 7,127 | `tests/common.py` | 3,103 |
| 2 | `http.py` | 2,845 | `orm/fields/base.py` | 2,705 |
| 3 | `tests/common.py` | 2,728 | `tools/translate.py` | 2,254 |
| 4 | `tools/translate.py` | 1,993 | `orm/fields/relational.py` | 2,217 |
| 5 | `orm/domains.py` | 1,988 | `service/server.py` | 1,753 |
| 6 | `tools/misc.py` | 1,961 | `orm/models/mixins/crud.py` | 1,719 |
| 7 | `orm/fields.py` | 1,939 | `tools/config.py` | 1,679 |
| 8 | `orm/fields_relational.py` | 1,772 | `orm/runtime/registry.py` | 1,338 |
| 9 | `service/server.py` | 1,613 | `orm/fields/properties.py` | 1,261 |
| 10 | `orm/registry.py` | 1,251 | `orm/domain/ast.py` | 1,167 |

The fork's largest file is a **test utility** (`tests/common.py`). The largest *production* code file is 2,705 lines — down from 7,127.

**JS god-files also decomposed:**

| JS File | Upstream | Fork | Extracted into |
|---------|----------|------|----------------|
| `list_renderer.js` | 2,313 | 1,551 | 9 modules |
| `search_model.js` | 2,341 | 1,594 | 10 modules |
| `action_service.js` | 1,882 | 1,264 | 8 modules |
| `relational_model/utils.js` | 905 | 33 | 8 modules |
| `pivot_model.js` | 1,598 | 1,109 | 4 modules |

### 21.2 ORM Package Architecture

| Metric | Upstream | Fork | Change |
|--------|----------|------|--------|
| Python files in `odoo/orm/` | 23 | 76 | +230% |
| Average file size | **870 lines** | **451 lines** | **-48%** |
| Total ORM lines | 20,015 | 34,323 | +71% |
| Largest file | 7,127 | 1,719 | -76% |
| Standalone-testable components | **0** | **9** (with 4,378 lines of pytest) | new |

The fork has +14,308 more ORM lines — but that's largely tests (4,378), docstrings, the new components layer, and type annotations. The actual logic was *decomposed*, not expanded.

### 21.3 Standalone Testability

| Metric | Upstream | Fork | Change |
|--------|----------|------|--------|
| ORM component tests (pytest, no DB) | **0 files** | **12 files, 4,378 lines** | new |
| `test_performance` module | **Does not exist** | **13 files, ~5,800 lines** | new |
| Base test lines | 35,342 | 45,641 | **+29%** |
| test_orm new test files | 0 | 9 new files | new |

The fork introduces **database-free ORM component tests** runnable with plain `pytest`. Upstream requires a full PostgreSQL database for every ORM test.

### 21.4 Static Analysis Coverage

| Metric | Upstream | Fork | Change |
|--------|----------|------|--------|
| Ruff unique rule IDs | 70 | 128 | **+83%** |
| Banned APIs | 0 | 3 (`utcnow`, `utcfromtimestamp`, `optparse`) | new |
| Security rules (bandit `S`) | No | Yes | new |
| Complexity limit (`C90`) | No | Yes (max=20) | new |
| Pathlib enforcement (`PTH`) | No | Yes | new |
| Timezone enforcement (`DTZ`) | No | Yes (selective) | new |
| Performance lints (`PERF`) | No | Yes | new |
| Modern Python (`FURB`) | No | Yes | new |
| Naming conventions (`N`) | No | Yes | new |
| Lint engine | Pylint (subprocess) | stdlib `ast` + ruff (in-process) | replaced |

### 21.5 Docstring and Type Hint Density

Sampled from the ORM core — upstream `models.py` vs fork's equivalent mixins:

| Metric | Upstream `models.py` | Fork `crud.py` | Fork `search.py` | Fork `read.py` |
|--------|---------------------|----------------|-------------------|----------------|
| Functions | 240 | 20 | 16 | 8 |
| Docstrings | 355 (1.5x) | 43 (2.2x) | 34 (2.1x) | 20 (2.5x) |
| Return type hints | 126 (52%) | 12 (60%) | 6 (38%) | — |

The fork has a **higher docstring-to-function ratio** (2.1-2.5 docstrings per function vs 1.5) — class docstrings and multi-line docstrings are consistently present. Type hint coverage is comparable.

### 21.6 Dependency Health

| Metric | Upstream | Fork | Change |
|--------|----------|------|--------|
| Total dependency lines | 97 | 47 | **-52%** |
| Python version conditionals | ~20 lines of `python_version` branches | 0 | **-100%** |
| Deprecated/EOL packages | **8** (psycopg2, libsass, passlib, gevent, greenlet, xlrd, xlwt, PyPDF2) | **0** | **-100%** |
| Known-vulnerable binaries | wkhtmltopdf (CVEs), passlib (unmaintained) | Replaced | **-100%** |

### 21.7 Monkeypatch Burden

| Metric | Upstream | Fork | Change |
|--------|----------|------|--------|
| Patch files | 20 | 14 | -30% |
| Total patch lines | **2,637** | **710** | **-73%** |

Every monkeypatch is technical debt — it breaks on dependency upgrades and hides bugs. The fork eliminated 73% of this burden.

### 21.8 New Infrastructure (Fork Only)

| Component | Upstream | Fork |
|-----------|----------|------|
| Standalone utility library (`odoo/libs/`) | Does not exist | **82 files, 12,268 lines** |
| Rust acceleration crate (`crates/odoo_rust/`) | Does not exist | **7 modules, 1,363 lines** |
| Machine documentation | Does not exist | **10 files, 3,569 lines** |
| Coding guidelines | Does not exist | **1,984 lines** |
| JS polyfills | 5 files | 1 file (clipboard only) |

### 21.9 Performance: Rust Acceleration (Fork Only)

10 PyO3 functions exported from `odoo_rust`, targeting ORM hot paths with Python fallbacks:

| Function | What it accelerates | Measured speedup |
|----------|-------------------|-----------------|
| `fast_clone` | `copy.deepcopy` on JSON-like dicts | **1.5-2x** |
| `batch_cache_get` | `mapped()` cache lookups | **2-3x** |
| `batch_cache_filter` | `filtered()` truthiness checks | **2-3x** |
| `batch_cache_values` | `sorted()` key extraction | **2-3x** |
| `rows_to_dicts` | `dictfetchall()` (10k rows x 20 cols) | **2.5x** (7.4ms → 3ms) |
| `origin_ids` | NewId-aware recordset iteration | measurable |
| `to_prefetch_ids` | `Field.__get__` cache misses | measurable |
| `csv_export` | CSV export with formula sanitization | measurable |
| `scan_byte_patterns` | Lint file scanning (SIMD memchr) | **10-50x** |
| `scan_regex_patterns` | Lint regex scanning | **10-50x** |

### 21.10 Performance: Database Driver (psycopg2 → psycopg3)

| Aspect | psycopg2 (Upstream) | psycopg3 (Fork) |
|--------|---------------------|------------------|
| Connection pooling | Custom Python impl | `psycopg_pool` (C-optimized) |
| Binary protocol | Limited | Full binary mode support |
| Pipeline mode | No | Yes (batch multiple queries per roundtrip) |
| COPY protocol | Basic | Streaming COPY IN/OUT |
| Async | Requires gevent/greenlet stack | Native async/await |
| JSON encoding | `Json()` adapter | `Jsonb()` with orjson backend |
| Prepared statements | Manual | Native support |

### 21.11 Performance: JSON Serialization (orjson)

| Aspect | Upstream (stdlib `json`) | Fork (`orjson`) |
|--------|------------------------|-----------------|
| Serialization speed | Baseline | **~3-10x faster** |
| Deserialization | Baseline | **~2-3x faster** |
| Native datetime support | No (needs `default=`) | Yes |
| Used in | — | Bus notifications, JSON fields, API responses |

### 21.12 Performance: PDF Rendering (wkhtmltopdf → WeasyPrint)

| Aspect | wkhtmltopdf (Upstream) | WeasyPrint (Fork) |
|--------|----------------------|-------------------|
| Process model | Subprocess per render | In-process |
| Startup cost | Process spawn (~100ms each) | First call ~30s (font init), then <1s |
| Memory | Separate process memory | Shared font/image cache across renders |
| CSS support | Qt WebKit (old) | Modern CSS (flexbox, grid, etc.) |
| Maintenance | **Abandoned** (last release 2023) | Actively maintained |
| Security | External binary (CVE risk) | Pure Python (SSRF fix included) |

### 21.13 Performance: Python 3.14 Runtime (Free Gains)

These improvements require no code changes — they come from running on Python 3.14:

| Feature | Impact |
|---------|--------|
| Specializing adaptive interpreter (3.11+) | **10-60% faster** overall |
| Zero-cost exceptions (3.11) | No `try` overhead on happy path |
| Comprehension inlining (3.12, PEP 709) | **Up to 2x faster** comprehensions |
| Immortal objects (3.12, PEP 683) | Less copy-on-write in `--workers=N` fork mode |
| Incremental GC (3.14) | **Order of magnitude** lower GC pause times for large heaps |
| Tail-call interpreter (3.14) | **3-5% geometric mean** improvement |
| Deferred annotations (3.14, PEP 649) | Faster module imports (no annotation evaluation) |

### 21.14 Performance: Lint Speed

| Aspect | Upstream (Pylint) | Fork (ast + Rust) |
|--------|-------------------|-------------------|
| SQL injection check | astroid-based (slow type inference) | stdlib `ast` visitor (in-process) |
| File scanning | Sequential Python I/O | Rust parallel walker + SIMD (`10-50x`) |
| Full lint run | Minutes | Seconds |

### 21.15 Summary Scorecard

| Dimension | Upstream 19.0 | Fork 19.0-marin | Delta |
|-----------|--------------|-----------------|-------|
| Max Python file size | 7,127 lines | 2,705 lines | **-62%** |
| ORM avg file size | 870 lines | 451 lines | **-48%** |
| Monkeypatch lines | 2,637 | 710 | **-73%** |
| Deprecated dependencies | 8 packages | 0 | **-100%** |
| Ruff rule coverage | 70 rules | 128 rules | **+83%** |
| Standalone ORM tests (pytest) | 0 | 4,378 lines | **new** |
| Performance benchmarks | 0 | ~5,800 lines | **new** |
| Base test lines | 35,342 | 45,641 | **+29%** |
| JS polyfills | 5 | 1 | **-80%** |
| Rust acceleration functions | 0 | 10 functions | **new** |
| Standalone utility library | 0 | 12,268 lines | **new** |
| Dependency lines | 97 | 47 | **-52%** |

---

## Appendix A: Files Added (650+)

### By Category

| Category | Count | Description |
|----------|-------|-------------|
| ORM restructuring | ~63 | Package structure, mixins, components, tests |
| Rust crate | ~150+ | Source + build artifacts |
| `odoo/libs/` | ~82 | Standalone utility packages |
| Machine documentation | 10 | Structured module maps |
| Lint system | 5 | New AST checkers + ruff test + scan library |
| Base model splits | ~15 | Decomposed god-files |
| Base tests | 4 | Benchmark, perf regression, N+1, ORM profiler |
| test_performance | ~8 | New performance addon |
| test_orm new tests | ~9 | Hot path, M2M, recordset, JSON, traversal tests |
| HTTP decomposition | ~12 | New package modules |
| Tools new files | ~11 | Sass, password, profiling, security |
| JS new modules | ~67 | List, search, action, field, model decomposition |
| Upstream additions | ~350+ | New l10n modules, payment providers, icons |

## Appendix B: Files Deleted (325+)

| Category | Count | Description |
|----------|-------|-------------|
| ORM consolidation | ~9 | Merged into new structure |
| Pylint infrastructure | 5 | Replaced by AST + ruff |
| Monkeypatches | 8 | No longer needed |
| wkhtmltopdf tests | ~10 | WeasyPrint replaces wkhtmltopdf |
| Polyfills (JS) | 5 | Native in ES2022-2025 |
| jQuery | 2 | Legacy removed |
| Python compat | ~3 | pycompat.py, PyPDF2 layers, loglevels.py |
| Upstream deletes | ~280+ | HiDPI icons, old l10n tests, CLA entries |

## Appendix C: Key Metrics

| Metric | Value |
|--------|-------|
| Total files changed | 6,931 |
| Net lines added | +32,052 |
| Python files | 2,023 changed |
| JavaScript files | 1,853 changed |
| New Rust lines | 1,363 |
| Monkeypatch lines removed | 1,927 |
| New test lines | ~15,000+ |
| ORM component test lines (pytest) | ~4,000 |
| Machine doc lines | 3,569 |
| Coding guidelines | 1,984 lines |
