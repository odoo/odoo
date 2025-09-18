import js from "@eslint/js";
import prettier from "eslint-plugin-prettier/recommended";
import simpleImportSort from "eslint-plugin-simple-import-sort";
import globals from "globals";

// ─────────────────────────────────────────────────────────────────────────────
// Whitelisted modules — only these are linted.
// Add new modules here as they are onboarded to ESLint.
// ─────────────────────────────────────────────────────────────────────────────
const COMMUNITY_MODULES = [
    "addons/web",
    "addons/board",
    "addons/base_import",
    "addons/bus",
    "addons/html_editor",
    "addons/html_builder",
    "addons/website",
    "addons/website_blog",
    "addons/web_tour",
    "addons/base_setup",
    "addons/purchase",
    "addons/spreadsheet",
    "addons/spreadsheet_account",
    "addons/spreadsheet_dashboard",
    "addons/spreadsheet_dashboard_account",
    "addons/spreadsheet_dashboard_hr_expense",
    "addons/spreadsheet_dashboard_pos_hr",
    "addons/spreadsheet_dashboard_sale",
    "addons/spreadsheet_dashboard_event_sale",
    // Mail & dependents
    "addons/calendar",
    "addons/hr",
    "addons/hr_holidays",
    "addons/hr_skills",
    "addons/im_livechat",
    "addons/mail",
    "addons/portal",
    "addons/snailmail",
    "addons/test_discuss_full",
    "addons/test_mail",
    "addons/website_livechat",
    "addons/website_slides",
    // POS
    "addons/point_of_sale",
    "addons/iot_drivers",
    "addons/l10n_ar_pos",
    "addons/l10n_co_pos",
    "addons/l10n_es_pos",
    "addons/l10n_fr_pos_cert",
    "addons/l10n_gcc_pos",
    "addons/l10n_in_pos",
    "addons/l10n_sa_pos",
    "addons/pos_adyen",
    "addons/pos_discount",
    "addons/pos_epson_printer",
    "addons/pos_hr",
    "addons/pos_hr_restaurant",
    "addons/pos_loyalty",
    "addons/pos_mrp",
    "addons/pos_online_payment",
    "addons/pos_online_payment_self_order",
    "addons/pos_restaurant",
    "addons/pos_restaurant_adyen",
    "addons/pos_restaurant_stripe",
    "addons/pos_sale",
    "addons/pos_sale_loyalty",
    "addons/pos_sale_margin",
    "addons/pos_self_order",
    "addons/pos_self_order_adyen",
    "addons/pos_self_order_epson_printer",
    "addons/pos_self_order_sale",
    "addons/pos_self_order_stripe",
    "addons/pos_stripe",
    // Misc
    "addons/l10n_br_website_sale",
];

const ENTERPRISE_MODULES = [
    "web_enterprise",
    "web_mobile",
    "web_studio",
    "web_cohort",
    "web_gantt",
    "web_grid",
    "web_map",
    "timesheet_grid",
    "timer",
    "industry_fsm",
    "helpdesk",
    "helpdesk_timesheet",
    "helpdesk_sale_timesheet",
    "planning",
    "project_enterprise",
    "documents",
    "documents_spreadsheet",
    "spreadsheet_edition",
    "spreadsheet_dashboard_crm",
    "spreadsheet_dashboard_edition",
    "spreadsheet_dashboard_documents",
    "spreadsheet_sale_management",
    "approvals",
    "test_discuss_full_enterprise",
    "test_mail_enterprise",
    "whatsapp",
    "voip",
    "stock_barcode",
    "stock_barcode_barcodelookup",
    "stock_barcode_mrp",
    "stock_barcode_mrp_subcontracting",
    "stock_barcode_picking_batch",
    "stock_barcode_product_expiry",
    "stock_barcode_quality_control",
    "stock_barcode_quality_control_picking_batch",
    "stock_barcode_quality_mrp",
    "sign",
    "sign_itsme",
    "mrp_workorder",
    "ai",
    "ai_livechat",
    "ai_website_livechat",
    // Enterprise POS
    "l10n_cl_edi_pos",
    "l10n_de_pos_cert",
    "l10n_de_pos_res_cert",
    "l10n_in_reports_gstr_pos",
    "l10n_mx_edi_pos",
    "l10n_pl_reports_pos_jpk",
    "l10n_br_edi_pos",
    "l10n_se_pos",
    "pos_account_reports",
    "pos_blackbox_be",
    "pos_enterprise",
    "pos_hr_mobile",
    "pos_iot",
    "pos_iot_six",
    "pos_online_payment_self_order_preparation_display",
    "pos_order_tracking_display",
    "pos_restaurant_appointment",
    "pos_restaurant_preparation_display",
    "pos_sale_stock_renting",
    "pos_self_order_preparation_display",
    "pos_settle_due",
    "pos_tyro",
];

// Build file globs: "addons/web/**/*.js" etc.
const allModuleGlobs = [...COMMUNITY_MODULES, ...ENTERPRISE_MODULES]
    .map((m) => `${m}/**/*.js`);


/** @type {import("eslint").Linter.Config[]} */
export default [
    // =========================================================================
    // Global ignores — blacklisted paths within whitelisted modules
    // =========================================================================
    {
        ignores: [
            // Libraries (vendored, not our code)
            "addons/web/static/lib/**",
            "!addons/web/static/lib/hoot/**",
            "addons/html_editor/static/lib/diff2html/*.js",
            "addons/spreadsheet/static/src/o_spreadsheet/o_spreadsheet.js",
            "voip/static/lib/**",

            // Legacy code (only top-level adapters are linted)
            "addons/web/static/src/legacy/**",
            "!addons/web/static/src/legacy/*.js",
            "web_enterprise/static/src/legacy/**",
            "!web_enterprise/static/src/legacy/*.js",
            "web_studio/static/src/legacy/**",
            "!web_studio/static/src/legacy/*.js",
            "web_cohort/static/src/legacy/**",
            "web_gantt/static/src/legacy/**",
            "web_map/static/src/legacy/**",
            "addons/base_import/static/src/legacy/**",

            // Legacy tests
            "addons/web/static/tests/**/legacy/*",
            "web_enterprise/static/tests/**/legacy/*",
            "web_studio/static/tests/**/legacy/*",
            "web_cohort/static/tests/legacy/**",
            "web_gantt/static/tests/legacy/**",
            "web_map/static/tests/legacy/**",
        ],
    },

    // =========================================================================
    // Base configuration (eslint:recommended + prettier)
    // =========================================================================
    js.configs.recommended,
    prettier,

    // =========================================================================
    // Main rules — applied to all whitelisted modules
    // =========================================================================
    {
        files: allModuleGlobs,
        plugins: {
            "simple-import-sort": simpleImportSort,
        },
        languageOptions: {
            ecmaVersion: "latest",
            sourceType: "module",
            globals: {
                ...globals.browser,
                // Odoo-specific globals
                odoo: "readonly",
                $: "readonly",
                jQuery: "readonly",
                Chart: "readonly",
                fuzzy: "readonly",
                StackTrace: "readonly",
                QUnit: "readonly",
                luxon: "readonly",
                py: "readonly",
                FullCalendar: "readonly",
                globalThis: "readonly",
                ScrollSpy: "readonly",
                module: "readonly",
                // Test frameworks
                chai: "readonly",
                describe: "readonly",
                it: "readonly",
                mocha: "readonly",
                // Libraries
                DOMPurify: "readonly",
                Prism: "readonly",
                // Bootstrap components
                Alert: "readonly",
                Collapse: "readonly",
                Dropdown: "readonly",
                Modal: "readonly",
                Offcanvas: "readonly",
                Popover: "readonly",
                Tooltip: "readonly",
            },
        },
        rules: {
            "prettier/prettier": ["error", {
                tabWidth: 4,
                semi: true,
                singleQuote: false,
                printWidth: 88,
                endOfLine: "auto",
            }],
            "no-undef": "error",
            "no-restricted-globals": ["error", "event", "self"],
            "no-const-assign": "error",
            "no-debugger": "error",
            "no-dupe-class-members": "error",
            "no-dupe-keys": "error",
            "no-dupe-args": "error",
            "no-dupe-else-if": "error",
            "no-unsafe-negation": "error",
            "no-duplicate-imports": "off",
            "simple-import-sort/imports": ["error", {
                groups: [
                    // Side effect imports
                    ["^\\u0000"],
                    // @odoo, @web, @mail, @point_of_sale, etc.
                    ["^@\\w"],
                    // Relative imports
                    ["^\\."],
                ],
            }],
            "simple-import-sort/exports": "error",
            "valid-typeof": "error",
            "no-unused-vars": ["error", {
                vars: "all",
                args: "none",
                ignoreRestSiblings: false,
                caughtErrors: "all",
            }],
            curly: ["error", "all"],
            "no-restricted-syntax": ["error", "PrivateIdentifier"],
            "prefer-const": ["error", {
                destructuring: "all",
                ignoreReadBeforeAssign: true,
            }],
            "arrow-body-style": ["error", "as-needed"],
        },
    },

    // =========================================================================
    // Service Worker override — `self` is the standard global
    // =========================================================================
    {
        files: ["**/service_worker.js"],
        rules: {
            "no-restricted-globals": ["error", "event"],
        },
    },

    // =========================================================================
    // Layer boundary enforcement (Feature-Sliced Design)
    //
    // Import direction is law — lower layers cannot import higher.
    // =========================================================================

    // ── Entity layer: model/ ─────────────────────────────────────────────
    {
        files: ["**/web/static/src/model/**/*.js"],
        rules: {
            "no-restricted-imports": ["error", {
                patterns: [
                    {
                        group: ["@web/views/*", "@web/search/*"],
                        message: "Entity layer cannot import widget layer. Use dependency injection.",
                    },
                    {
                        group: ["@web/webclient/*"],
                        message: "Entity layer cannot import page layer.",
                    },
                ],
            }],
        },
    },
    // ── Entity layer: core/domain.js ─────────────────────────────────────
    {
        files: ["**/web/static/src/core/domain.js"],
        rules: {
            "no-restricted-imports": ["error", {
                patterns: [
                    {
                        group: ["@web/views/*", "@web/search/*"],
                        message: "Entity layer cannot import widget layer. Use dependency injection.",
                    },
                    {
                        group: ["@web/webclient/*"],
                        message: "Entity layer cannot import page layer.",
                    },
                ],
            }],
        },
    },
    // ── Feature layer: fields/ ───────────────────────────────────────────
    {
        files: ["**/web/static/src/fields/**/*.js"],
        rules: {
            "no-restricted-imports": ["error", {
                patterns: [
                    {
                        group: ["@web/views/*"],
                        message: "Feature layer (fields/) cannot import widget layer (views/). Move shared code to core/ or use registry indirection.",
                    },
                    {
                        group: ["@web/search/*"],
                        message: "Feature layer (fields/) cannot import widget layer (search/).",
                    },
                    {
                        group: ["@web/webclient/*"],
                        message: "Feature layer cannot import page layer.",
                    },
                ],
            }],
        },
    },
    // ── Shared layer: core/ ──────────────────────────────────────────────
    {
        files: ["**/web/static/src/core/**/*.js"],
        rules: {
            "no-restricted-imports": ["error", {
                patterns: [
                    {
                        group: ["@web/views/*", "@web/search/*"],
                        message: "Shared layer cannot import widget layer.",
                    },
                    {
                        group: ["@web/webclient/*"],
                        message: "Shared layer cannot import page layer.",
                    },
                    {
                        group: ["@web/fields/*"],
                        message: "Shared layer cannot import feature layer.",
                    },
                ],
            }],
        },
    },
    // ── Shared layer: services/ ──────────────────────────────────────────
    {
        files: ["**/web/static/src/services/**/*.js"],
        rules: {
            "no-restricted-imports": ["error", {
                patterns: [
                    {
                        group: ["@web/views/*", "@web/search/*"],
                        message: "Shared layer cannot import widget layer.",
                    },
                    {
                        group: ["@web/webclient/*"],
                        message: "Shared layer cannot import page layer.",
                    },
                    {
                        group: ["@web/fields/*"],
                        message: "Shared layer cannot import feature layer.",
                    },
                ],
            }],
        },
    },
    // ── Shared layer: ui/ ─────────────────────────────────────────────────
    {
        files: ["**/web/static/src/ui/**/*.js"],
        rules: {
            "no-restricted-imports": ["error", {
                patterns: [
                    {
                        group: ["@web/views/*", "@web/search/*"],
                        message: "Shared layer (ui/) cannot import widget layer.",
                    },
                    {
                        group: ["@web/webclient/*"],
                        message: "Shared layer (ui/) cannot import page layer.",
                    },
                    {
                        group: ["@web/fields/*"],
                        message: "Shared layer (ui/) cannot import feature layer.",
                    },
                ],
            }],
        },
    },
    // ── Shared layer: components/ ─────────────────────────────────────────
    {
        files: ["**/web/static/src/components/**/*.js"],
        rules: {
            "no-restricted-imports": ["error", {
                patterns: [
                    {
                        group: ["@web/views/*", "@web/search/*"],
                        message: "Shared layer (components/) cannot import widget layer.",
                    },
                    {
                        group: ["@web/webclient/*"],
                        message: "Shared layer (components/) cannot import page layer.",
                    },
                    {
                        group: ["@web/fields/*"],
                        message: "Shared layer (components/) cannot import feature layer.",
                    },
                ],
            }],
        },
    },
];
