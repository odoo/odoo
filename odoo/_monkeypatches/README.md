# Odoo Monkeypatches

This directory contains runtime patches for Python standard library and third-party modules that fix compatibility issues, security vulnerabilities, or performance problems.

## Architecture

### How It Works

1. Submodules are named after the module they patch (e.g., `xlsxwriter.py` patches `xlsxwriter`)
2. Each submodule defines a `patch_module()` function
3. The `PatchImportHook` in `__init__.py` intercepts imports and calls `patch_module()`:
   - If the target module is already imported: patch immediately
   - Otherwise: patch right after the module is imported

### The name is the wiring, so it cannot lie

`patch_init()` derives the hook set from the file names; nothing else declares
what a file patches. A file named for a module it does not touch still runs —
it is hooked on that module's import, which for a stdlib module means "at
boot" — so the mechanism cannot tell the difference, and the index inherits
the lie. `site.py` was that file: it patched `odoo`, `encodings.aliases`,
`codecs` and `babel.core`, and nothing named `site`. Bootstrap that patches no
module at all belongs in `patch_init()` only while it must run before any
third-party import -- the `TZ` pin is the one such step -- and nowhere in this
package otherwise: the `evented` argv surgery moved to `cli/command.py`, where
argv is parsed.

### Importing a patch submodule applies its patch

`odoo._monkeypatches.<target>` is hooked alongside `<target>` itself, because
the two orders have to converge. A patch submodule imports its own target at
module level, so importing the submodule first re-enters `patch_module()` while
the submodule is still initializing and its `patch_module()` does not yet
exist. That call defers; the submodule's own `_PatchingLoader` applies the
patch when exec finishes.

Before that, the re-entrant call returned silently and the patch was **dropped
for the life of the process** — with no log, and with the name absent from
`_APPLIED`, so nothing downstream could tell. `TestMonkeypatchContract` walked
every submodule with `importlib.import_module`, and thereby disabled 9 of the
14 patches it was asserting about: `csv` never got its `UNIX` dialect, so
`tools/translate.py` would have raised `csv.Error: unknown dialect`.

`applied()` returns the set that has actually run. A hooked name missing from
it is deferred, waiting for its target's import — not failed.

## Patch Index

> **This index is enforced.** `tooling/architecture/package_index_check.py`
> fails CI if a module in this directory is missing from the tables below, or if
> they name a module that no longer exists. The check reads only this section,
> so *Removal Criteria* and *Recently Removed* below stay free to name modules
> that are gone.

### Standard Library Patches

| File | Purpose | Type |
|------|---------|------|
| `ast.py` | Bound `ast.literal_eval()`'s input (default 100KiB, `ODOO_LIMIT_LITEVAL_BUFFER`). Resolved once at patch time, not per call | SECURITY |
| `codecs.py` | Charset labels CPython will not resolve: a search function for the separator-less ISO-8859-8-E/I spellings | COMPAT |
| `csv.py` | Raise the field size limit from 128KiB to 500MiB, so an inlined base64 image is one readable field | PERF |
| `email.py` | Replace `email.policy.SMTP` so identification headers (`Message-Id`, `References`, `Resent-Message-ID`, ...) are never folded and user headers fold only at the RFC 5322 limit of 998 chars | COMPAT |
| `locale.py` | Add missing `D_FMT`, `T_FMT` constants and `nl_langinfo()` for Windows. Inert on POSIX | COMPAT |
| `mimetypes.py` | Pin six extensions (fonts, `.webp`, `.svg`, `.js`) against a host `/etc/mime.types` or Windows registry that overrides CPython's table. All six match CPython 3.14's own defaults, so this only has to win against host config — and it wraps `init()`, which would otherwise discard the pins on any rebuild | COMPAT |
| `re.py` | Raise the pattern cache from 512 to 4096 entries. Odoo's working set does exceed the stdlib floor — 872 distinct patterns at a `-u base` boot, 1341 over a 3261-test `/base` run — but the **measured** end-to-end saving is small: 86.7ms → 80.4ms of compile time per boot, 389.6ms → 366.6ms per test run. Patterns are overwhelmingly compiled once and held in module globals, so eviction rarely costs a recompile | PERF |

### Web Framework Patches

| File | Purpose | Type |
|------|---------|------|
| `werkzeug.py` | Route `Request`/`Response` JSON through `odoo.libs.json.scriptsafe` (XSS safety) | COMPAT |
| `bs4.py` | Suppress `XMLParsedAsHTMLWarning` from BeautifulSoup 4.11.0+ (ofxparse compatibility) | COMPAT |

### Spreadsheet Patches

| File | Purpose | Type |
|------|---------|------|
| `xlsxwriter.py` | Sanitize Excel sheet names through odoo/libs/sheet_names.py (all four of xlsxwriter's rules, including de-duplicating the clashes truncation creates); default `strings_to_formulas` off, so an exported cell starting `=` is never a live formula | COMPAT |

### PDF Patches

| File | Purpose | Type |
|------|---------|------|
| `pypdf.py` | Two patches `tools/pdf` used to apply inline: `DictionaryObject.get` returns its default instead of propagating `KeyError`, and `NameObject.renumber_table` gains the delimiters and control characters PDF name objects must escape. (A third patch that overrode `filters.decompress` for truncated-stream tolerance was removed: stock pypdf's `decompress` already retries past a truncated tail while also enforcing `ZLIB_MAX_OUTPUT_LENGTH`, which the override did not.) | COMPAT |

### Text Processing Patches

| File | Purpose | Type |
|------|---------|------|
| `num2words.py` | Register `odoo.libs.locale.BulgarianNumerals` with num2words 0.5.14, which ships no `bg`. The converter is a language implementation, not a patch, and lives in `libs/` | FEATURE |
| `docutils.py` | Stand in for the Sphinx domain (`:meth:`, `:class:`, … as literals; `deprecated`/`attribute` as notes that keep their argument) so docstring RST renders without depending on Sphinx | COMPAT |
| `lxml.py` | Widen `lxml.html.defs.link_attrs` with `xlink:href`, which `HtmlMixin.iterlinks()` reads as a local default, so `ir_module._get_desc` rewrites SVG links in a module description. The cleaner does not consult it (`lxml_html_clean` carries its own `_tag_link_attrs`), so sanitisation is unaffected | FEATURE |

### Internationalization Patches

| File | Purpose | Type |
|------|---------|------|
| `babel.py` | Alias bare `nb` to `nb_NO`, so `Request.best_lang` resolves an `Accept-Language: nb` browser instead of raising `KeyError` into "no preference" | COMPAT |

## Patch Types

- **SECURITY**: Fixes security vulnerabilities
- **BUGFIX**: Fixes bugs in third-party libraries
- **COMPAT**: Ensures compatibility across versions/platforms
- **PERF**: Performance optimizations
- **FEATURE**: Adds functionality not available in upstream

## Adding a New Patch

1. Create `<target_module>.py` in this directory
2. Implement `patch_module()`, and put the explanation in **its** docstring —
   not at module level. Say why the patch exists and what would let it go
3. Add a row to the Patch Index above, and a *Removal Criteria* entry
4. The patch will be auto-detected and applied

The docstring goes on the function, not on the module. That is where every
patch here already carries its rationale, and where a reader lands from a
traceback:

```python
import target_module


def patch_module() -> None:
    """One line on what this patch fixes.

    Why it is needed, what upstream does instead, and the condition under
    which it can be deleted.
    """
    target_module.some_function = patched_function
```

## What belongs here

A patch, and only the patch. `num2words.py` used to be 250 lines of Bulgarian
numeral logic wrapped around a one-line registration; the language now lives in
`odoo/libs/locale/cardinals_bg.py`, where it is Odoo-agnostic code in the
package for Odoo-agnostic code and its tests run DB-free in Tier 1 rather than
needing `-i base`. If a file here is mostly *implementation*, the implementation
has a better home and the registration stays.

The same rule sent the `UNIX` csv dialect to `tools/translate.py`: configuration
that is ours, consumed in one place, does not belong in a third-party registry
under a global name.

## Removal Criteria

Patches should be removed when:

| Patch | Remove When |
|-------|-------------|
| `num2words.py` | Bulgarian is added to upstream num2words |
| `locale.py` | Windows support is dropped OR Python stdlib adds Windows support |
| `bs4.py` | ofxparse fixes XML parsing issue (#170) |
| `mimetypes.py` | No supported host can override CPython's table for these six |
| `babel.py` | Babel ships an `nb` entry in `LOCALE_ALIASES` |
| `codecs.py` | CPython resolves `iso88598i`/`iso88598e` (the cp874 half was met by the 3.14 floor and removed 2026-08) |

## Recently Removed

| Patch | Removed | Reason |
|-------|---------|--------|
| `urllib3.py` | 2026-02 | urllib3 2.x sets `pool_classes_by_scheme` per-instance; Odoo never mutates it |
| `werkzeug.py` (URL API) | 2026-02 | Migrated to `urllib.parse` (stdlib); ~1045 lines removed |
| `lxml.py` (the 5.2.0 compat fix) | 2026-02 | Fixed in lxml >= 5.2.0 (current: 6.0.2). **Not** the current `lxml.py`, which is a later, unrelated `link_attrs` widening — see the Patch Index |
| `xlrd.py` | 2026-02 | xlrd 2.x removed xlsx support; defusedxml not installed |
| `zeep.py` | 2026-02 | Fixed in zeep >= 4.3.1 (notation visitor bug #1185) |
| `email.py` (policy-clone validation) | 2026-02 | Python 3.12+ natively validates attributes in `_PolicyBase.clone()`. **Not** the current `email.py`, which is a later, unrelated patch for header folding — see the Patch Index. |
| `pytz.py` | 2026-02 | Migrated to zoneinfo (stdlib); see `odoo/libs/datetime/tz.py` |
| `xlwt.py` | 2026-02 | xlwt is abandoned (last release 2017); migrated to xlsxwriter |
| `stdnum.py` | 2026-08 | Obsolete **and broken**. python-stdnum 2.2 sets `operation_timeout` itself in `_get_zeep_soap_client`, which `requirements-addons.txt` already recorded as the reason for the pin; meanwhile stdnum grew a third `verify` parameter that the replacement never had, so every VIES/UID/RNC/TCKimlik lookup raised `TypeError` -- uncaught, since `account_vat`'s `_compute_vies_valid` only handles `OSError`/`InvalidComponent`/`zeep.exceptions.Fault`. The replacement also dropped `session.verify`, i.e. TLS verification config. |
| `smtplib.py` | 2026-08 | Unreachable. It replaced `SMTP._print_debug` on the class, but the only caller (`ir_mail_server.py`) assigns the identical function to the *instance* two lines before its `set_debuglevel()`, so the class-level one was never invoked -- and it hard-coded an addon's logger name into core. |
| `site.py` | 2026-08 | Split, not deleted: it was named for a module it did not patch. The codec/alias half is `codecs.py`, the Babel half is `babel.py`, and the `evented` argv surgery -- not a module patch at all -- is `cli/command.py`'s `_select_run_mode()`, run first thing in `main()`. |
| `werkzeug.py` (MultiDict.deepcopy) | 2026-08 | Werkzeug 3.x already takes `memo`; the wrapper dropped it, which turned a working cycle-safe `copy.deepcopy` into `RecursionError`. |
| `werkzeug.py` (Rule._get_func_code) | 2026-08 | An `assert isinstance(code, CodeType)` over a parameter werkzeug already annotates `CodeType`, stripped entirely under `-O`. |
| `csv.py` (the `UNIX` dialect) | 2026-08 | Not a patch: Odoo's own dialect, registered under a global name in the stdlib registry, with exactly one caller. It now lives beside that caller as `tools/translate.py::_UnixDialect`, where it cannot be reached by name from anywhere and does not depend on a monkeypatch having run first. |

## Statistics

- **Total**: 16 files (15 patches + 1 utility)
- **By type**: COMPAT (9), PERF (2), SECURITY (1), FEATURE (2)

These are re-derived from the directory and the Patch Index by
`tooling/architecture/package_index_check.py`, so they cannot drift again — the
previous figures said 12 patches against a directory holding 14.
