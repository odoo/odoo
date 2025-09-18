# Odoo Monkeypatches

This directory contains runtime patches for Python standard library and third-party modules that fix compatibility issues, security vulnerabilities, or performance problems.

## Architecture

### How It Works

1. Submodules are named after the module they patch (e.g., `xlsxwriter.py` patches `xlsxwriter`)
2. Each submodule defines a `patch_module()` function
3. The `PatchImportHook` in `__init__.py` intercepts imports and calls `patch_module()`:
   - If the target module is already imported: patch immediately
   - Otherwise: patch right after the module is imported

### Naming Conventions

- `<module>.py` - Patches for module `<module>` (auto-detected)
- `_<name>.py` - Utility modules, NOT auto-detected as patches

## Patch Index

### Standard Library Patches

| File | Purpose | Type |
|------|---------|------|
| `ast.py` | Limit `ast.literal_eval()` buffer to prevent segfaults (default 100KiB, configurable via `ODOO_LIMIT_LITEVAL_BUFFER`) | SECURITY |
| `csv.py` | Increase field size limit from 128KiB to 500MiB for image imports; register UNIX dialect | PERF |
| `locale.py` | Add missing `D_FMT`, `T_FMT` constants and `nl_langinfo()` for Windows | COMPAT |
| `mimetypes.py` | Register missing MIME types: fonts (.woff, .eot, .ttf), .webp, .svg, .js | COMPAT |
| `re.py` | Increase regex cache from 512 to 4096 entries | PERF |

### Web Framework Patches

| File | Purpose | Type |
|------|---------|------|
| `werkzeug.py` | Patch json_module (XSS safety), FileStorage.save, MultiDict.deepcopy, Rule._get_func_code | COMPAT |
| `bs4.py` | Suppress `XMLParsedAsHTMLWarning` from BeautifulSoup 4.11.0+ (ofxparse compatibility) | COMPAT |

### Spreadsheet Patches

| File | Purpose | Type |
|------|---------|------|
| `xlsxwriter.py` | Sanitize Excel sheet names (remove invalid chars, limit to 31 chars) | COMPAT |
| `_excel_utils.py` | Shared utilities for Excel sheet name sanitization | UTIL |

### Text Processing Patches

| File | Purpose | Type |
|------|---------|------|
| `num2words.py` | Add Bulgarian language support (not in upstream num2words) | FEATURE |
| `docutils.py` | Add dummy Sphinx domain elements to avoid Sphinx dependency | COMPAT |

### Core Patches

| File | Purpose | Type |
|------|---------|------|
| `site.py` | Gevent monkey patching, codec aliases, Babel locale patching | COMPAT |

## Patch Types

- **SECURITY**: Fixes security vulnerabilities
- **BUGFIX**: Fixes bugs in third-party libraries
- **COMPAT**: Ensures compatibility across versions/platforms
- **PERF**: Performance optimizations
- **FEATURE**: Adds functionality not available in upstream

## Adding a New Patch

1. Create `<target_module>.py` in this directory
2. Add a docstring explaining the patch
3. Implement `patch_module()` function
4. The patch will be auto-detected and applied

```python
"""
Brief description of what this patch fixes.

More details about why this patch is needed and when it can be removed.
"""
import target_module


def patch_module():
    # Apply your patches here
    target_module.some_function = patched_function
```

## Removal Criteria

Patches should be removed when:

| Patch | Remove When |
|-------|-------------|
| `num2words.py` | Bulgarian is added to upstream num2words |
| `locale.py` | Windows support is dropped OR Python stdlib adds Windows support |
| `bs4.py` | ofxparse fixes XML parsing issue (#170) |
| `mimetypes.py` | Python stdlib registers correct MIME types on all platforms |

## Recently Removed

| Patch | Removed | Reason |
|-------|---------|--------|
| `urllib3.py` | 2026-02 | urllib3 2.x sets `pool_classes_by_scheme` per-instance; Odoo never mutates it |
| `werkzeug.py` (URL API) | 2026-02 | Migrated to `urllib.parse` (stdlib); ~1045 lines removed |
| `lxml.py` | 2026-02 | Fixed in lxml >= 5.2.0 (current: 6.0.2) |
| `xlrd.py` | 2026-02 | xlrd 2.x removed xlsx support; defusedxml not installed |
| `zeep.py` | 2026-02 | Fixed in zeep >= 4.3.1 (notation visitor bug #1185) |
| `stdnum.py` | 2026-02 | Fixed in python-stdnum >= 2.0 (operation_timeout #444) |
| `email.py` | 2026-02 | Python 3.12+ natively validates attributes in `_PolicyBase.clone()` |
| `pytz.py` | 2026-02 | Migrated to zoneinfo (stdlib); see `odoo/libs/datetime/tz.py` |
| `xlwt.py` | 2026-02 | xlwt is abandoned (last release 2017); migrated to xlsxwriter |

## Statistics

- **Total patches**: 9 files (8 patches + 1 utility)
- **By category**: stdlib (5), web (2), spreadsheet (1+1 util), text (2), core (1)
- **By type**: COMPAT (5), PERF (2), SECURITY (1), FEATURE (1)
