# Base Module Test Tags

Test organization, tagging strategy, and execution reference for `core/odoo/addons/base/tests/`.

## Quick Reference

```bash
# All base tests (~1347 methods, ~195 classes)
--test-tags '/base' -u base

# Only post_install tests
--test-tags '/base,post_install' -u base

# Exclude slow/benchmark tests
--test-tags '/base,-base_benchmark,-base_perf,-slow' -u base

# Specific topic
--test-tags '/base,res_partner' -u base
--test-tags '/base,profiling' -u base
--test-tags '/base,mail_server' -u base

# Single test class
--test-tags '/base:TestACL' -u base

# Single test method
--test-tags '/base:TestACL.test_field_groups' -u base
```

## Tag Inventory

### Install Phase Tags

| Tag | Classes | Meaning |
|-----|---------|---------|
| `post_install` + `-at_install` | 39 | Run only after module installation |
| _(no install tag)_ | ~156 | Run in both at_install and post_install |

> The `post_install, -at_install` combination is **always** used together.
> No class uses `post_install` without `-at_install` or vice versa.

### Feature Tags

| Tag | Classes | Files | Purpose |
|-----|---------|-------|---------|
| `res_partner` | 12 | test_res_partner.py | Partner model tests |
| `test_retry` | 12 | test_test_retry.py | Test retry mechanism |
| `test_retry_success` | 8 | test_test_retry.py | Successful retry scenarios |
| `profiling` | 4 | test_profiler.py | Code profiling |
| `nodatabase` | 3 | test_profiler.py, test_tests_tags.py | No database required |
| `mail_server` | 2 | test_ir_mail_server.py | SMTP server tests |
| `mail_sanitize` | 2 | test_mail.py | HTML sanitization |
| `nplusone` | 2 | test_nplusone.py | N+1 query detection |
| `profiler` | 2 | test_orm_profiler.py | ORM profiler |
| `test_retry_failures` | 2 | test_test_retry.py | Retry failure scenarios |
| `test_retry_disable` | 2 | test_test_retry.py | Retry disabled tests |
| `stock` | 2 | test_cloc.py, test_display_name.py | Stock module tests |
| `mail_tools` | 1 | test_mail.py | Email utilities |
| `groups` | 1 | test_res_users.py | Group management |
| `res_partner_address` | 1 | test_res_partner.py | Address-specific tests |
| `test_eval_context` | 1 | test_ir_model.py | Expression context |
| `migration` | 1 | test_ir_filters.py | Migration tests |
| `neutralize` | 1 | test_neutralize.py | DB neutralization |
| `deprecation` | 1 | test_deprecation.py | Deprecation warnings |

### Performance/Quality Tags

| Tag | Classes | Purpose |
|-----|---------|---------|
| `-standard` | 15 | Excluded from standard test runs |
| `slow` | 5 | Tests taking > 1 second |
| `base_benchmark` | 1 | Benchmark performance suite |
| `base_perf` | 1 | Performance regression detection |
| `profiling_performance` | 1 | Profiler performance tests |
| `profiling_memory` | 1 | Memory profiler tests |

### Test Infrastructure Tags

| Tag | Classes | Purpose |
|-----|---------|---------|
| `nightly` | 1 | Nightly-only tests |
| `fast` | 1 | Fast running tests |
| `flow` | 1 | Feature flow tests |
| `standard` | 1 | Standard test suite marker |

## Base Test Classes

### From `tests/common.py`

| Class | Parent | Purpose |
|-------|--------|---------|
| `TransactionCaseWithUserDemo` | TransactionCase | Pre-loads `base.user_demo` + company context |
| `HttpCaseWithUserDemo` | HttpCase | HTTP tests with demo user |
| `SavepointCaseWithUserDemo` | TransactionCase | Savepoint isolation with demo user |
| `TransactionCaseWithUserPortal` | TransactionCase | Pre-loads `base.demo_user0` (portal) |
| `HttpCaseWithUserPortal` | HttpCase | HTTP tests with portal user |

### Custom Base Classes (in test files)

| Class | File | Parent | Purpose |
|-------|------|--------|---------|
| `TestRetryCommon` | test_test_retry.py | TransactionCase | Base for retry tests (12 subclasses) |
| `FormatAddressCase` | test_format_address_mixin.py | TransactionCase | Address formatting utilities |
| `UsersCommonCase` | test_res_users.py | TransactionCase | User test setup |
| `TestCommonCustomFields` | test_ir_actions.py | TransactionCase | Custom fields setup |
| `ViewCase` | test_views.py | TransactionCase | View validation utilities |
| `TransactionExpressionCase` | test_expression.py | TransactionCase | Domain expression utilities |

## Test File Reference

### Tagged Files (31 files, 134 classes)

| File | Tags | Classes | Tests | Base Class |
|------|------|---------|-------|------------|
| `test_base_benchmark.py` | `post_install, -at_install, base_benchmark` | 1 | 13 | TransactionCase |
| `test_base_perf_regression.py` | `post_install, -at_install, base_perf` | 1 | 12 | TransactionCase |
| `test_cloc.py` | `post_install, -at_install, -standard, stock` | 3 | 6 | TransactionCase |
| `test_deprecation.py` | `post_install, -at_install, deprecation` | 1 | 2 | TransactionCase |
| `test_display_name.py` | `post_install, -at_install, stock` | 1 | 3 | TransactionCase |
| `test_expression.py` | _mixed tags_ | 9 | 83 | TransactionCase, SavepointCase |
| `test_form_create.py` | `post_install, -at_install` | 1 | 7 | TransactionCase |
| `test_http_case.py` | `post_install, -at_install` | 9 | 13 | HttpCase, BaseCase |
| `test_import_files.py` | `post_install, -at_install` | 1 | 1 | TransactionCase |
| `test_ir_actions.py` | `post_install, -at_install` | 5 | 44 | TransactionCase |
| `test_ir_asset.py` | `post_install, -at_install` | 1 | 1 | TransactionCase |
| `test_ir_filters.py` | `post_install, -at_install, migration` | 4 | 6 | TransactionCase |
| `test_ir_http.py` | `post_install, -at_install` | 1 | 1 | TransactionCase |
| `test_ir_mail_server.py` | `post_install, -at_install, mail_server` | 3 | 16 | TransactionCase |
| `test_ir_model.py` | `post_install, -at_install` + `test_eval_context` | 5 | 16 | TransactionCase |
| `test_mail.py` | `post_install, -at_install, mail_sanitize/mail_tools` | 4 | 45 | BaseCase |
| `test_neutralize.py` | `post_install, -at_install, neutralize` | 1 | 1 | TransactionCase |
| `test_nplusone.py` | `post_install, -at_install, nplusone` | 2 | 8 | TransactionCase |
| `test_orm.py` | `post_install, -at_install` _(partial)_ | 3 | 19 | TransactionCase |
| `test_orm_profiler.py` | `post_install, -at_install, profiler` | 2 | 9 | TransactionCase |
| `test_overrides.py` | `post_install, -at_install` | 1 | 4 | TransactionCase |
| `test_profiler.py` | `post_install, -at_install, profiling` + variants | 6 | 25 | BaseCase, HttpCase, TransactionCase |
| `test_qweb.py` | `post_install, -at_install` | 4 | 98 | BaseCase, TransactionCase |
| `test_res_config.py` | `post_install, -at_install` | 2 | 8 | TransactionCase |
| `test_res_country.py` | `post_install, -at_install` | 1 | 1 | TransactionCase |
| `test_res_partner.py` | `res_partner` + variants | 5 | 35 | TransactionCase |
| `test_res_users.py` | `post_install, -at_install` + `groups` | 5 | 21 | TransactionCase |
| `test_tests_tags.py` | `nodatabase, nightly, fast` _(meta tests)_ | 4 | 12 | BaseCase |
| `test_test_retry.py` | `test_retry` + variants | 13 | 19 | TransactionCase |
| `test_translate.py` | `post_install, -at_install` | 10 | 84 | TransactionCase |
| `test_views.py` | `post_install, -at_install` | 25 | 174 | TransactionCase |

### Untagged Files (54 files)

These run in **both** at_install and post_install phases by default.

**Core ORM & Database:**
- `test_acl.py` — ACL enforcement
- `test_api.py` — API decorators
- `test_base.py` — safe_eval, parent_store, groups
- `test_cache.py` — Record cache
- `test_db_cursor.py` — Cursor management
- `test_float.py` — Float precision
- `test_groups.py` — Group management
- `test_ir_attachment.py` — Attachment CRUD + permissions
- `test_ir_cron.py` — Cron execution
- `test_ir_default.py` — Default values
- `test_ir_sequence.py` — Sequences standard + no_gap
- `test_ormcache.py` — ORM cache
- `test_search.py` — Search operations
- `test_transactions.py` — Transaction environments

**Utilities & Tools:**
- `test_barcode.py` — Barcode generation
- `test_cli.py` — CLI commands
- `test_configmanager.py` — Config management
- `test_config_parameter.py` — System parameters
- `test_date_utils.py` — Date utilities
- `test_func.py` — Frozendict, Lazy
- `test_image.py` — Image processing
- `test_intervals.py` — Interval operations
- `test_misc.py` — Miscellaneous utilities
- `test_mimetypes.py` — MIME detection
- `test_module.py` — Module operations
- `test_module_graph.py` — Module dependency graph
- `test_pdf.py` — PDF operations
- `test_query.py` — SQL query building
- `test_signature.py` — Digital signatures
- `test_sql.py` — SQL tools
- `test_tz.py` — Timezone handling

**Data Models:**
- `test_avatar_mixin.py` — Avatar generation
- `test_format_address_mixin.py` — Address formatting
- `test_i18n.py` — Internationalization
- `test_ir_embedded_actions.py` — Embedded actions
- `test_ir_mail_server_smtpd.py` — SMTP daemon tests
- `test_ir_module.py` — Module system
- `test_ir_module_category.py` — Module categories
- `test_ir_sequence_date_range.py` — Date range sequences
- `test_menu.py` — Menu tree
- `test_num2words_ar.py` — Arabic number words
- `test_res_company.py` — Company hierarchy
- `test_res_currency.py` — Currency conversion
- `test_res_lang.py` — Language management
- `test_res_partner_bank.py` — Bank accounts
- `test_res_partner_merge.py` — Partner merge

**Reports & QWeb:**
- `test_reports.py` — Report rendering
- `test_qweb_field.py` — QWeb field widgets

**Test Infrastructure:**
- `test_basecase.py` — Base test case validation
- `test_init.py` — Module initialization
- `test_install.py` — Module installation
- `test_test_suite.py` — Test suite infrastructure
- `test_uninstall.py` — Module uninstallation
- `test_user_has_group.py` — Group membership

## Statistics

| Metric | Value |
|--------|-------|
| Total test files | 85 |
| Total test classes | 260 |
| Total test methods | 1347 |
| Files with @tagged | 31 (36%) |
| Files without @tagged | 54 (64%) |
| Classes using post_install | 39 |
| Unique tags | 33 |
| Largest test file | test_views.py (25 classes, 174 tests) |

## Running Focused Tests

```bash
# Fast feedback — core ORM only (~5s)
--test-tags '/base:TestACL' -u base

# Partner tests (~30s)
--test-tags '/base,res_partner' -u base

# Skip views (largest file, 25 classes)
--test-tags '/base,-/base:TestViews,-/base:TestDebugger' -u base

# Only profiling
--test-tags '/base,profiling' -u base

# Only retry mechanism
--test-tags '/base,test_retry' -u base

# Performance regression
--test-tags '/base,base_perf' -u base

# Skip slow and benchmarks for quick iteration
--test-tags '/base,-base_benchmark,-base_perf,-slow,-profiling' -u base
```
