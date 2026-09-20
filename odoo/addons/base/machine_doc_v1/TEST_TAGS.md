# Base Module Test Tags

Test organization, tagging strategy, and execution reference for `odoo/addons/base/tests/`.

## Quick Reference

```bash
# All base tests (3984 methods, 808 classes, 140 files)
--test-tags '/base' -u base

# Only post_install tests
--test-tags '/base,post_install' -u base

# Exclude slow/benchmark tests
--test-tags '/base,-base_perf,-slow' -u base

# Specific topic
--test-tags '/base,res_partner' -u base
--test-tags '/base,profiling' -u base

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
| `nplusone` | 2 | test_nplusone.py | N+1 query detection |
| `profiler` | 2 | test_orm_profiler.py | ORM profiler |
| `test_retry_failures` | 2 | test_test_retry.py | Retry failure scenarios |
| `test_retry_disable` | 2 | test_test_retry.py | Retry disabled tests |
| `stock` | 2 | test_cloc.py, test_display_name.py | Stock module tests |
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

### Tagged Files (80 files, 476 classes)

| File | Tags | Classes | Tests | Base Class |
|------|------|---------|-------|------------|
| `test_base_language_wizards_audit.py` | `post_install`, `-at_install` | 1 | 6 | TransactionCase |
| `test_base_module_wizards.py` | `post_install`, `-at_install` | 1 | 6 | TransactionCase |
| `test_base_perf_regression.py` | `post_install`, `-at_install`, `base_perf` | 1 | 14 | TransactionCase |
| `test_change_password_wizard_audit.py` | `post_install`, `-at_install` | 1 | 4 | TransactionCase |
| `test_cloc.py` | `post_install`, `-at_install` | 3 | 6 | TransactionCase |
| `test_copy.py` | `post_install`, `-at_install` | 1 | 5 | TransactionCase |
| `test_decimal_precision_audit.py` | `post_install`, `-at_install` | 1 | 4 | TransactionCase |
| `test_depends_completeness.py` | `-standard`, `depends_sweep` | 3 | 5 | TransactionCase |
| `test_deprecation.py` | `-at_install`, `post_install`, `deprecation` | 1 | 2 | TransactionCase |
| `test_device_log_isolation.py` | `post_install`, `-at_install` | 1 | 2 | TransactionCase |
| `test_display_name.py` | `-at_install`, `post_install` | 1 | 3 | TransactionCase |
| `test_expression.py` | `res_partner` | 8 | 89 | SavepointCaseWithUserDemo, TransactionExpressionCase, TransactionCase |
| `test_field_description_audit.py` | `post_install`, `-at_install` | 3 | 8 | TransactionCase, TransactionCaseWithUserDemo |
| `test_form_create.py` | `-at_install`, `post_install` | 5 | 21 | TransactionCase |
| `test_framework_contracts.py` | `post_install`, `-at_install` | 1 | 5 | TransactionCase |
| `test_groups.py` | `at_install`, `groups`, `post_install`, `-at_install` | 6 | 33 | BaseCase, TransactionCase |
| `test_http_case.py` | `-at_install`, `post_install` | 10 | 26 | HttpCase, TestRequestRemainingCommon, TestChromeBrowser |
| `test_id_sequence_names.py` | `post_install`, `-at_install` | 1 | 3 | TransactionCase |
| `test_import_files.py` | `post_install`, `-at_install` | 4 | 109 | TransactionCase |
| `test_ir_actions.py` | `post_install`, `-at_install` | 7 | 104 | TestServerActionsBase, TransactionCase, TestCommonCustomFields |
| `test_ir_actions_audit.py` | `post_install`, `-at_install` | 51 | 156 | TransactionCase |
| `test_ir_actions_reach.py` | `post_install`, `-at_install` | 1 | 2 | TransactionCase |
| `test_ir_actions_report_audit.py` | `post_install`, `-at_install` | 6 | 15 | TransactionCase |
| `test_ir_actions_server_audit.py` | `post_install`, `-at_install` | 3 | 8 | TransactionCase |
| `test_ir_actions_server_regressions.py` | `post_install`, `-at_install` | 21 | 56 | ServerActionCase |
| `test_ir_actions_tree.py` | `post_install`, `-at_install` | 3 | 16 | TransactionCase |
| `test_ir_actions_webhook.py` | `post_install`, `-at_install` | 4 | 20 | WebhookCase, TransactionCase |
| `test_ir_asset.py` | `-at_install`, `post_install` | 1 | 1 | TransactionCase |
| `test_ir_asset_audit.py` | `post_install`, `-at_install` | 20 | 69 | TransactionCase |
| `test_ir_attachment.py` | `post_install`, `-at_install` | 10 | 172 | TransactionCaseWithUserDemo, TransactionCaseWithUserPortal, TransactionCase |
| `test_ir_autovacuum_audit.py` | `post_install`, `-at_install` | 3 | 9 | TransactionCase |
| `test_ir_binary.py` | `post_install`, `-at_install` | 6 | 13 | TransactionCase, TransactionCaseWithUserDemo |
| `test_ir_cron.py` | `post_install`, `-at_install` | 13 | 91 | TransactionCase, CronMixinCase, TransactionCaseWithUserDemo, TestIrCron, BaseCase |
| `test_ir_cron_audit.py` | `post_install`, `-at_install` | 2 | 5 | TransactionCase |
| `test_ir_default_audit.py` | `post_install`, `-at_install` | 1 | 5 | TransactionCase |
| `test_ir_demo.py` | `post_install`, `-at_install` | 4 | 8 | TransactionCase |
| `test_ir_filters.py` | `post_install`, `-at_install`, `migration` | 8 | 32 | FiltersCase, TransactionCase |
| `test_ir_job.py` | `post_install`, `-at_install` | 8 | 114 | TransactionCase, BaseCase |
| `test_ir_logging.py` | `post_install`, `-at_install` | 3 | 7 | TransactionCase |
| `test_ir_model.py` | `-at_install`, `post_install`, `test_eval_context` | 14 | 140 | TransactionCase, HttpCase |
| `test_ir_model_data.py` | `post_install`, `-at_install` | 2 | 5 | TransactionCase |
| `test_mixin_merge.py` | `post_install`, `-at_install` | 2 | 7 | TransactionCase |
| `test_module_data_remove_xmlid_records.py` | `post_install`, `-at_install` | 1 | 2 | TransactionCase |
| `test_module_data_rename_in_view_arches.py` | `post_install`, `-at_install` | 1 | 5 | TransactionCase |
| `test_module_data_rename_model.py` | `post_install`, `-at_install` | 2 | 10 | TransactionCase |
| `test_module_data_rename_module.py` | `post_install`, `-at_install` | 1 | 5 | TransactionCase |
| `test_neutralize.py` | `post_install`, `-at_install`, `neutralize` | 2 | 2 | TransactionCase, BaseCase |
| `test_nplusone.py` | `-standard`, `nplusone` | 3 | 12 | TransactionCase, TestNplusOneDetection |
| `test_orm.py` | `post_install`, `-at_install` | 6 | 30 | TransactionCase |
| `test_orm_profiler.py` | `-standard`, `profiler` | 2 | 9 | TransactionCase |
| `test_ormcache.py` | `-at_install`, `post_install` | 2 | 7 | BaseCase, TransactionCase |
| `test_overrides.py` | `-at_install`, `post_install` | 1 | 4 | TransactionCase |
| `test_partner_identifier_confidentiality.py` | `post_install`, `-at_install` | 2 | 11 | TransactionCase |
| `test_partner_private_address_access.py` | `post_install`, `-at_install` | 1 | 11 | TransactionCase |
| `test_profiler.py` | `post_install`, `-at_install`, `profiling`, `-standard`, `profiling_performance`, `profiling_memory` | 7 | 39 | TransactionCase, BaseCase, HttpCase |
| `test_qweb.py` | `post_install`, `-at_install` | 27 | 227 | TransactionCase, TransactionCaseWithUserDemo |
| `test_report_paperformat_audit.py` | `post_install`, `-at_install` | 1 | 10 | TransactionCase |
| `test_res_company.py` | `post_install`, `-at_install` | 4 | 22 | TransactionCase |
| `test_res_config.py` | `post_install`, `-at_install` | 3 | 12 | TransactionCase |
| `test_res_config_install.py` | `post_install`, `-at_install` | 1 | 2 | TransactionCase |
| `test_res_country.py` | `-at_install`, `post_install` | 2 | 4 | TransactionCase |
| `test_res_partner.py` | `res_partner`, `res_partner_address`, `post_install`, `-at_install` | 16 | 104 | TransactionCaseWithUserDemo, TransactionCase |
| `test_res_partner_identifier.py` | `post_install`, `-at_install` | 1 | 18 | TransactionCase |
| `test_res_partner_main_channels.py` | `post_install`, `-at_install` | 1 | 15 | TransactionCase |
| `test_res_partner_merge.py` | `post_install`, `-at_install`, `res_partner_merge` | 10 | 34 | TransactionCase |
| `test_res_partner_sync.py` | `res_partner`, `res_partner_sync` | 1 | 10 | TransactionCase |
| `test_res_users.py` | `post_install`, `-at_install`, `groups` | 30 | 100 | UsersCommonCase, TransactionCase, HttpCase |
| `test_res_users_apikeys.py` | `post_install`, `-at_install` | 1 | 24 | TransactionCase |
| `test_res_users_identitycheck.py` | `post_install`, `-at_install` | 1 | 5 | TransactionCase |
| `test_res_users_log.py` | `post_install`, `-at_install` | 2 | 5 | TransactionCase |
| `test_res_users_settings.py` | `post_install`, `-at_install` | 4 | 16 | TransactionCase |
| `test_seeded_users.py` | `-at_install`, `post_install` | 1 | 3 | HttpCaseWithUserDemo, HttpCaseWithUserPortal |
| `test_table_object_conversion.py` | `post_install`, `-at_install` | 2 | 8 | TransactionCase |
| `test_test_retry.py` | `test_retry`, `test_retry_success`, `-standard`, `test_retry_failures`, `test_retry_disable` | 12 | 19 | TestRetryCommon, TransactionCase |
| `test_tests_tags.py` | `nodatabase` | 4 | 14 | TransactionCase, BaseCase |
| `test_translate.py` | `post_install`, `-at_install` | 12 | 89 | BaseCase, TransactionCase |
| `test_view_payload.py` | `post_install`, `-at_install` | 1 | 3 | TransactionCase |
| `test_view_provenance.py` | `post_install`, `-at_install` | 1 | 5 | TransactionCase |
| `test_views.py` | `post_install`, `-at_install`, `-standard`, `migration`, `render_all_views`, `post_install_l10n`, `at_install`, `modifiers` | 57 | 309 | TransactionCase, ViewCase, BaseCase, TransactionCaseWithUserDemo |
| `test_x2many_cache_scope.py` | `post_install`, `-at_install` | 4 | 13 | TransactionCase |

### Untagged Files (60 files)

These run in **both** at_install and post_install phases by default.

- `test_acl.py` — ACL enforcement
- `test_api.py` — API decorators
- `test_avatar_mixin.py` — Avatar generation
- `test_backend_integration.py` — TestAmountToTextBackend
- `test_barcode.py` — Barcode generation
- `test_base.py` — safe_eval, parent_store, groups
- `test_basecase.py` — Base test case validation
- `test_cache.py` — Record cache
- `test_cache_scan_predicates.py` — TestCacheScanPredicates
- `test_catalog_mixin.py` — TestCatalogMixin
- `test_cli.py` — CLI commands
- `test_config_parameter.py` — System parameters
- `test_configmanager.py` — Config management
- `test_date_utils.py` — Date utilities
- `test_db_cursor.py` — Cursor management
- `test_default_group.py` — TestDefaultGroup
- `test_depends_audit.py` — TestDependsAudit
- `test_export_import_roundtrip.py` — TestExportImportRoundtrip
- `test_float.py` — Float precision
- `test_format_address_mixin.py` — Address formatting
- `test_i18n.py` — Internationalization
- `test_image.py` — Image processing
- `test_init.py` — Module initialization
- `test_install.py` — Module installation
- `test_inverse_cache_alignment.py` — Inverse-write cache pruning, `env.ref` memo
- `test_ir_actions_server_ssrf.py` — TestWebhookSsrfGuard
- `test_ir_attachment_storage.py` — TestIrAttachmentStorage, TestMemoryStorageCRUD
- `test_ir_default.py` — Default values
- `test_ir_embedded_actions.py` — Embedded actions
- `test_ir_http.py` — TestIrHttpAuth
- `test_ir_module.py` — Module system
- `test_ir_module_category.py` — Module categories
- `test_ir_sequence.py` — Sequences standard + no_gap
- `test_ir_sequence_date_range.py` — Date range sequences
- `test_log_access_cache.py` — TestLogAccessCache
- `test_menu.py` — Menu tree
- `test_misc.py` — Miscellaneous utilities
- `test_mixin_profiler.py` — TestMixinProfiler
- `test_module.py` — Module operations needing a database (the manifest,
- `test_num2words_ar.py` — Arabic number words
- `test_pdf.py` — PDF operations
- `test_populate.py` — TestPopulate
- `test_properties_base_definition.py` — TestPropertiesBaseDefinition
- `test_query.py` — SQL query building
- `test_qweb_field.py` — QWeb field widgets
- `test_res_currency.py` — Currency conversion
- `test_res_lang.py` — Language management
- `test_res_partner_bank.py` — Bank accounts
- `test_search.py` — Search operations
- `test_signature.py` — Digital signatures
- `test_sort_collation.py` — TestSortCollation
- `test_sql.py` — SQL tools
- `test_tag_tag.py` — TestTagTag, TestTagCode
- `test_test_suite.py` — Test suite infrastructure
- `test_transactions.py` — Transaction environments
- `test_tz.py` — Timezone handling
- `test_unaccent_parity.py` — TestUnaccentParity
- `test_uninstall.py` — Module uninstallation
- `test_user_has_group.py` — Group membership
- `test_xml_utils.py` — XSD validation from attachment and remote archive

## Statistics

| Metric | Value |
|--------|-------|
| Total test files | 140 |
| Total test classes | 808 |
| Total test methods | 3984 |
| Files with @tagged | 80 (57%) |
| Files without @tagged | 60 (43%) |
| Classes using post_install | 271 |
| Unique tags | 28 |
| Largest test file | test_db_cursor.py (117 classes, 389 tests) |

Counted as unittest collects them: a method whose name starts with `test`, not
`test_` — a `testCamelCase` method would run too, so it is counted. A class with
no test method is a shared base and is not counted. `factcheck.sh --update`
regenerates every figure above and the header line under Quick Reference.

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
--test-tags '/base,-base_perf,-slow,-profiling' -u base
```

Device-log error containment: `test_device_log_isolation.py` verifies that a rejected optional SQL write preserves the request transaction and an unchanged trace performs no SQL.
