import js from "@eslint/js";
import prettier from "eslint-plugin-prettier/recommended";
import simpleImportSort from "eslint-plugin-simple-import-sort";
import globals from "globals";

// ─────────────────────────────────────────────────────────────────────────────
// Onboarded modules — these get the full Odoo ruleset below. Every other
// .js/.mjs in the repo is still linted, by `js.configs.recommended` plus
// prettier (neither carries a `files` key, so both apply repo-wide); the lane
// is a hard zero over all of it. Add a module here to onboard it.
// ─────────────────────────────────────────────────────────────────────────────
const COMMUNITY_MODULES = [
    "addons/api_doc",
    "addons/barcodes",
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
    "addons/gamification",
    "addons/survey",
    "addons/project",
    "addons/resource",
    "addons/mass_mailing",
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
    "addons/auth_portal",
    "addons/snailmail",
    "addons/test_discuss_full",
    "addons/test_mail",
    "addons/website_livechat",
    "addons/website_slides",
    // POS
    "addons/point_of_sale",
    "addons/iot",
    "addons/iot_blackbox_be",
    "addons/iot_drivers",
    "addons/l10n_ar_pos",
    "addons/l10n_co_pos",
    "addons/l10n_es_pos",
    "addons/l10n_fr_pos_cert",
    "addons/l10n_gcc_pos",
    "addons/l10n_in_pos",
    "addons/l10n_sa_pos",
    "addons/l10n_tw_edi_ecpay_pos",
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
    // Accounting / stock / sale / mrp stack (onboarded to ESLint)
    "addons/account",
    "addons/account_tax",
    "addons/analytic",
    "addons/product",
    "addons/uom",
    "addons/stock",
    "addons/stock_account",
    "addons/sale",
    "addons/sale_stock",
    "addons/mrp",
    "addons/purchase_stock",
    "addons/l10n_tw_edi_ecpay_website_sale",
    // The framework package itself (not an addon): odoo/tools, odoo/tests and
    // the JS shipped by the core test addons under odoo/addons. Onboarded
    // wholesale — the full ruleset cost only 9 findings beyond what the
    // repo-wide `js.configs.recommended` + prettier blocks already caught.
    "odoo",
];

// Enterprise modules live in a SEPARATE repo (addons/enterprise), so these
// globs are meaningless relative to THIS config's directory — ESLint 10 roots
// every glob at the config file's own directory. They are exported for
// addons/enterprise/eslint.config.mjs, which re-uses `makeConfig` below so both
// repos share one ruleset. Do not add them to the default export: from here
// they match nothing and only create the illusion of coverage.
export const ENTERPRISE_MODULES = [
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
    "document",
    "document_spreadsheet",
    "spreadsheet_edition",
    "spreadsheet_dashboard_crm",
    "spreadsheet_dashboard_edition",
    "spreadsheet_dashboard_document",
    "spreadsheet_sale_management",
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

// Paths ignored regardless of which repo consumes this config.
const SHARED_IGNORES = [
    // Vendored third-party libraries (not our code) live under
    // <module>/static/lib/ and are ignored wholesale — by convention,
    // vendored code goes in static/lib and nowhere else, so it is
    // excluded structurally rather than via a per-library allowlist
    // (which always drifts). Putting a third-party file anywhere else is
    // the bug; fix it by relocating into static/lib, not by listing it.
    //
    // Written as `/**/*` (files) rather than `/**` (files AND the directory):
    // a pattern that ignores the directory prunes the traversal, and then a
    // negation such as COMMUNITY_IGNORES' `!addons/web/static/lib/hoot/**`
    // cannot re-include anything, because the directory is never descended
    // into. Ignoring only the files keeps those negations effective.
    "**/static/lib/**/*",
    // TypeScript declaration files. Every `files:` glob in this config is
    // *.js, so a .d.ts matched no block and eslint reported "File ignored
    // because no matching configuration was supplied" -- a WARNING that reads
    // like a finding but means eslint had no opinion at all. It cannot form
    // one: espree does not parse TypeScript and no TS parser is a dependency
    // here. Declared rather than left to fall through, so the boundary is a
    // decision someone can find. What covers them instead: tsc, whose
    // tsconfig include is **/*.ts so declaration files are its native input,
    // and the prettier_dts gate, which holds their formatting at zero drift
    // the way prettier_scss does for Sass -- formatting being the one thing
    // eslint would otherwise have enforced here, via eslint-plugin-prettier.
    "**/*.d.ts",
];

const COMMUNITY_IGNORES = [
    // hoot is first-party despite living under web/static/lib (historical).
    "!addons/web/static/lib/hoot/**",
    // Vendored bundle that predates the convention. TODO: relocate under
    // static/lib so this special case can go away too.
    "addons/spreadsheet/static/src/o_spreadsheet/o_spreadsheet.js",

    // Generated Store-serialization contract whose body must stay
    // strict JSON (parsed by json.loads in
    // mail/tests/test_mock_server_contract.py). Formatting it produces
    // valid JS but invalid JSON and breaks that test. Mirrored in
    // .prettierignore.
    "addons/mail/static/tests/mock_server/contract/store_shapes.js",
    // Same shape: the frozen view IR fixture's body is parsed by json.loads
    // in odoo/tools/tests/test_view_ir_fixture.py. Mirrored in
    // .prettierignore.
    "addons/web/static/tests/views/view_ir_fixture.js",

    // Legacy code (only top-level adapters are linted)
    "addons/web/static/src/legacy/**",
    "!addons/web/static/src/legacy/*.js",
    "addons/base_import/static/src/legacy/**",

    // Legacy tests
    "addons/web/static/tests/**/legacy/*",

    // Asset-bundle fixtures, not code. Each is a single `var x = N;` whose
    // MINIFIED text is asserted byte-for-byte in the concatenated bundle by
    // test_assetsbundle/tests/test_assetsbundle.py (`var a=1;;` etc.), so the
    // declaration is load-bearing: `no-unused-vars` wants it deleted and
    // `no-var` wants `let`, and either "fix" rewrites the expected output of
    // ~10 tests. Ignored at the config level rather than with an inline
    // eslint-disable because a comment inside the file is minifier-dependent
    // — the bundle these tests assert on is exactly what must not change.
    "odoo/addons/test_assetsbundle/static/src/js/*.js",
];

// Consumed by addons/enterprise/eslint.config.mjs — see ENTERPRISE_MODULES.
export const ENTERPRISE_IGNORES = [
    // Legacy code (only top-level adapters are linted)
    "web_studio/static/src/legacy/**",
    "!web_studio/static/src/legacy/*.js",
    "web_cohort/static/src/legacy/**",
    "web_gantt/static/src/legacy/**",
    "web_map/static/src/legacy/**",

    // Legacy tests
    "web_studio/static/tests/**/legacy/*",
    "web_cohort/static/tests/legacy/**",
    "web_gantt/static/tests/legacy/**",
    "web_map/static/tests/legacy/**",
];

// no-console — incremental rollout; see the config block below.
const COMMUNITY_NO_CONSOLE_MODULES = [
    "addons/web",
    "addons/mail",
    "addons/point_of_sale",
    "addons/purchase",
    "addons/bus",
    "addons/account",
    "addons/account_tax",
    "addons/analytic",
    "addons/product",
    "addons/uom",
    "addons/stock",
    "addons/stock_account",
    "addons/sale",
    "addons/sale_stock",
    "addons/mrp",
    "addons/purchase_stock",
    "addons/html_editor",
    "addons/web_tour",
    "addons/website",
    "addons/im_livechat",
    "addons/l10n_tw_edi_ecpay_website_sale",
];

/**
 * Build the shared Odoo ESLint ruleset, scoped to one repo's modules.
 *
 * ESLint 10 resolves every `files`/`ignores` glob relative to the directory of
 * the config file that is actually loaded. A single config in addons/odoo can
 * therefore never reach addons/enterprise: enterprise globs silently match zero
 * files. Each repo instead ships its own thin eslint.config.mjs that calls this
 * factory, so the rules live here once and the paths stay repo-local.
 *
 * @param {object}   options
 * @param {string[]} options.modules           Module dirs to lint, repo-relative.
 * @param {string[]} [options.ignores]         Extra ignore globs, repo-relative.
 * @param {string[]} [options.noConsoleModules] Modules scrubbed of stray console.*.
 * @returns {import("eslint").Linter.Config[]}
 */
// A relative import with no extension resolves nowhere under native ESM: the
// browser fetches the raw path, which a per-file bundle serves as a 404 and the
// module graph fails silently. `./map_model` took the whole settings page down.
const EXTENSIONLESS_RELATIVE_IMPORT = {
    regex: "^\\.\\.?/(?!.*\\.(?:js|xml|scss|json)$)",
    message:
        "Relative import without an extension: under native ESM the browser fetches the raw path and a per-file bundle 404s it. Use the bare '@addon/...' specifier.",
};

export function makeConfig({ modules, ignores = [], noConsoleModules = [] }) {
    // Build file globs: "addons/web/**/*.js" etc.
    //
    // `.mjs` is included deliberately. Node-side code in the tree (the asset
    // pipeline's es-module-lexer worker, tooling helpers) is written as `.mjs`,
    // and a bare `*.js` glob left those files matched ONLY by the repo-wide
    // `js.configs.recommended` + prettier — silently exempt from eqeqeq,
    // no-var, prefer-const, curly, arrow-body-style, simple-import-sort and
    // no-restricted-globals. They looked linted (eslint reported them, clean)
    // while the half of the ruleset that carries the standards never ran.
    const allModuleGlobs = modules.map((m) => `${m}/**/*.{js,mjs}`);

    return [
        // =========================================================================
        // Global ignores — blacklisted paths within whitelisted modules
        // =========================================================================
        {
            ignores: [...SHARED_IGNORES, ...ignores],
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
                // Deliberately optionless: eslint-plugin-prettier resolves the
                // nearest .prettierrc.json for each file, and rule options passed
                // here would SHADOW it — giving two sources of truth that drift
                // silently (eslint and the `prettier` CLI would then disagree on
                // the same file). Each repo ships its own .prettierrc.json, which
                // is required anyway: prettier resolves config from the file's own
                // directory upward, and addons/enterprise is a sibling tree that
                // can never reach addons/odoo's copy. Keep the two in sync.
                "prettier/prettier": "error",
                "no-undef": "error",
                "no-restricted-globals": ["error", "event", "self"],
                eqeqeq: ["error", "smart"],
                "no-var": "error",
                "no-const-assign": "error",
                "no-debugger": "error",
                "no-dupe-class-members": "error",
                "no-dupe-keys": "error",
                "no-dupe-args": "error",
                "no-dupe-else-if": "error",
                "no-unsafe-negation": "error",
                // Intentional error-swallowing is spelled `catch {}`; the rule
                // otherwise only accepts it when a comment sits inside the block.
                "no-empty": ["error", { allowEmptyCatch: true }],
                "no-duplicate-imports": "off",
                "simple-import-sort/imports": [
                    "error",
                    {
                        groups: [
                            // Side effect imports
                            ["^\\u0000"],
                            // @odoo, @web, @mail, @point_of_sale, etc.
                            ["^@\\w"],
                            // Relative imports
                            ["^\\."],
                        ],
                    },
                ],
                "simple-import-sort/exports": "error",
                "valid-typeof": "error",
                "no-unused-vars": [
                    "error",
                    {
                        vars: "all",
                        args: "none",
                        ignoreRestSiblings: false,
                        caughtErrors: "all",
                    },
                ],
                curly: ["error", "all"],
                "no-restricted-syntax": [
                    "error",
                    "PrivateIdentifier",
                    {
                        // H-5 Pattern 4 smell detector — state-management
                        // review 2026-04-19.  A setter inside a
                        // ``reactive({...})`` literal conflates state with
                        // effects: the setter runs SIDE effects on other
                        // reactive state when ``obj.foo = x`` is written,
                        // hiding a data-flow edge the signal system can't
                        // reason about.  Express the effect explicitly with
                        // ``useEffect(() => ..., () => [obj.foo])`` and
                        // keep the signal itself a plain field.
                        //
                        // The escape hatch — read-only caching / pure
                        // derivation — only needs a getter (no setter), so
                        // this selector only fires on ``set``.
                        selector:
                            "CallExpression[callee.name='reactive'] > ObjectExpression > Property[kind='set']",
                        message:
                            "Pattern 4 smell: setters inside reactive({...}) conflate state with effects. Use plain reactive({foo: null}) + useEffect for side effects, or a SignalStore subclass for computation. See machine_doc_v1/STATE_MANAGEMENT.md §Pattern 4.",
                    },
                ],
                "prefer-const": [
                    "error",
                    {
                        destructuring: "all",
                        ignoreReadBeforeAssign: true,
                    },
                ],
                "arrow-body-style": ["error", "as-needed"],
            },
        },

        // =========================================================================
        // no-console — incremental rollout
        //
        // Keeps stray console.log/debug/info out of shipped code (warn/error are
        // allowed for genuine diagnostics). Enforced only on the modules cleaned so
        // far; add module globs here as each one is scrubbed, the same way modules
        // are onboarded to ESLint above. The test-file and tooling-scripts blocks
        // below turn this back off for those trees (they run later, so they win).
        // Dedicated logging/debug/QA utilities opt out with a file-level disable.
        // =========================================================================
        ...(noConsoleModules.length
            ? [
                  {
                      files: noConsoleModules.map((m) => `${m}/**/*.js`),
                      rules: {
                          "no-console": ["error", { allow: ["warn", "error"] }],
                      },
                  },
              ]
            : []),

        // =========================================================================
        // Test files (Hoot environment) — all modules, whitelisted or not
        //
        // Hoot's primitives (test/expect/describe…) are IMPORTED from "@odoo/hoot",
        // so they never need to be globals. What test files in NON-whitelisted
        // modules were missing is the base browser environment: they are linted by
        // `js.configs.recommended` (which has no `files` key, so it applies
        // repo-wide) but only whitelisted modules got `globals.browser` above —
        // every `no-undef` hit in static/tests was a browser global (document,
        // window, console, Event, …) or `odoo`. Declare them here for every
        // module's test tree; for whitelisted modules this merges harmlessly with
        // the main block.
        // =========================================================================
        {
            files: ["**/static/tests/**/*.js"],
            languageOptions: {
                globals: {
                    ...globals.browser,
                    odoo: "readonly",
                    luxon: "readonly",
                    QUnit: "readonly",
                },
            },
            rules: {
                // Debug logging in tests is fine.
                "no-console": "off",
                // Under native ESM, module identity is keyed by resolved URL, so a
                // relative `../src/...` import and the canonical `@addon/...` bare
                // specifier for the same file resolve to TWO distinct module
                // instances. Tests that imported source that way got duplicate
                // class references, breaking `instanceof`/`Array.includes` identity
                // checks (e.g. plugin-set membership) and silently 404'ing on the
                // un-normalized path. Always import addon source via its bare
                // specifier. The old odoo.define loader hid this by normalizing
                // paths; native ESM does not.
                "no-restricted-imports": [
                    "error",
                    {
                        patterns: [
                            {
                                group: ["**/../src/**", "**/src/*"],
                                message:
                                    "Do not import addon source from a test via a relative '../src/...' path — under native ESM it resolves to a DUPLICATE module instance (breaks class identity / plugin-set membership and 404s the un-normalized URL). Use the canonical bare specifier, e.g. `@html_editor/...` or `@web/...`.",
                            },
                            EXTENSIONLESS_RELATIVE_IMPORT,
                        ],
                    },
                ],
            },
        },

        // =========================================================================
        // Source files — all modules, whitelisted or not
        //
        // The same gap as the test tree above, on the other side of static/: a
        // module not yet onboarded is still matched by `js.configs.recommended`,
        // and without the browser environment every `document`, `window`,
        // `setTimeout` or `odoo` it touched was a `no-undef` — 597 of them across
        // 120 modules, none saying anything about the code. Browser code gets
        // the browser environment; onboarding a module adds the ruleset.
        // =========================================================================
        {
            files: ["**/static/src/**/*.js"],
            languageOptions: {
                globals: {
                    ...globals.browser,
                    odoo: "readonly",
                    luxon: "readonly",
                },
            },
            rules: {
                "no-restricted-imports": [
                    "error",
                    { patterns: [EXTENSIONLESS_RELATIVE_IMPORT] },
                ],
            },
        },

        // Google Maps arrives through a <script> tag on the page, so `google`
        // is a real global there and nowhere else.
        {
            files: ["**/website_google_map/static/src/**/*.js"],
            languageOptions: {
                globals: {
                    google: "readonly",
                },
            },
        },

        // =========================================================================
        // Service Worker override — `self` is the standard global
        // =========================================================================
        {
            // `*service_worker.js` and not `service_worker.js`: enterprise's
            // `push_service_worker.js` is one too, and matched only the
            // dedicated-worker block below, which carries the wrong globals.
            files: ["**/*service_worker.js"],
            languageOptions: {
                globals: {
                    ...globals.serviceworker,
                },
            },
            rules: {
                "no-restricted-globals": ["error", "event"],
            },
        },

        // Web/dedicated workers (e.g. discuss tick_worker.js) — eslint 10 dropped
        // `/* eslint-env worker */` comments, so declare the worker globals here.
        {
            files: ["**/*_worker.js", "**/worker/*.js"],
            languageOptions: {
                globals: {
                    ...globals.worker,
                },
            },
        },

        // =========================================================================
        // Node tooling scripts — build/typecheck helpers, not browser code
        //
        // Files under an addon's tooling/ tree run under Node, so they
        // legitimately use `process`,
        // `console`, etc. They are matched by `js.configs.recommended` (no `files`
        // key → repo-wide, and eslint lints .mjs by default) but were never given
        // the main block's browser globals — which is correct, they aren't browser
        // code; they just also lacked Node's. Declare the Node environment for them
        // so their `process`/`console` use stops tripping `no-undef`.
        //
        // tools/assets/js/ is the same situation outside tooling/: the asset
        // pipeline spawns those files as a real Node child process (see
        // `shutil.which("node")` in odoo/tools/assets/esm_lexer.py), so they talk
        // over process.stdin/stdout. Note the worker there is `.mjs`, so the
        // `**/*_worker.js` block below never applied to it — and that block grants
        // WEB-worker globals, which are the wrong environment for it anyway.
        // =========================================================================
        {
            files: [
                "**/tooling/**/*.{js,mjs,cjs}",
                "**/tools/assets/js/**/*.{js,mjs,cjs}",
            ],
            languageOptions: {
                globals: {
                    ...globals.node,
                },
            },
            rules: {
                // CLI tooling prints to stdout/stderr — console is its output.
                "no-console": "off",
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
                "no-restricted-imports": [
                    "error",
                    {
                        patterns: [
                            {
                                group: ["@web/views/*", "@web/search/*"],
                                message:
                                    "Entity layer cannot import widget layer. Use dependency injection.",
                            },
                            {
                                group: ["@web/webclient/*"],
                                message: "Entity layer cannot import page layer.",
                            },
                            EXTENSIONLESS_RELATIVE_IMPORT,
                        ],
                    },
                ],
            },
        },
        // ── Entity layer: core/domain.js ─────────────────────────────────────
        {
            files: ["**/web/static/src/core/domain.js"],
            rules: {
                "no-restricted-imports": [
                    "error",
                    {
                        patterns: [
                            {
                                group: ["@web/views/*", "@web/search/*"],
                                message:
                                    "Entity layer cannot import widget layer. Use dependency injection.",
                            },
                            {
                                group: ["@web/webclient/*"],
                                message: "Entity layer cannot import page layer.",
                            },
                            EXTENSIONLESS_RELATIVE_IMPORT,
                        ],
                    },
                ],
            },
        },
        // ── Feature layer: fields/ ───────────────────────────────────────────
        {
            files: ["**/web/static/src/fields/**/*.js"],
            rules: {
                "no-restricted-imports": [
                    "error",
                    {
                        patterns: [
                            {
                                group: ["@web/views/*"],
                                message:
                                    "Feature layer (fields/) cannot import widget layer (views/). Move shared code to core/ or use registry indirection.",
                            },
                            {
                                group: ["@web/search/*"],
                                message:
                                    "Feature layer (fields/) cannot import widget layer (search/).",
                            },
                            {
                                group: ["@web/webclient/*"],
                                message: "Feature layer cannot import page layer.",
                            },
                            EXTENSIONLESS_RELATIVE_IMPORT,
                        ],
                    },
                ],
            },
        },
        // ── Shared layer: core/ ──────────────────────────────────────────────
        // The shared tier is ORDERED: core < ui < components. It used to be flat,
        // and that is what let `services/` grow inside it importing freely across
        // all three.
        {
            files: ["**/web/static/src/core/**/*.js"],
            rules: {
                "no-restricted-imports": [
                    "error",
                    {
                        patterns: [
                            {
                                group: ["@web/ui/*", "@web/components/*"],
                                message:
                                    "core/ is the floor of the shared tier: it owns no surface, so it cannot import ui/ or components/. File the module with what it serves instead.",
                            },
                            {
                                group: ["@web/model/*"],
                                message: "Shared layer cannot import entity layer.",
                            },
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
                            EXTENSIONLESS_RELATIVE_IMPORT,
                        ],
                    },
                ],
            },
        },
        // ── Shared layer: ui/ ─────────────────────────────────────────────────
        {
            files: ["**/web/static/src/ui/**/*.js"],
            rules: {
                "no-restricted-imports": [
                    "error",
                    {
                        patterns: [
                            {
                                group: ["@web/components/*"],
                                message:
                                    "Overlay infrastructure sits BELOW the widgets that use it: a widget opens a popover, a popover does not know what a widget is. A single-purpose service belongs next to the component it renders.",
                            },
                            {
                                group: ["@web/model/*"],
                                message:
                                    "Shared layer (ui/) cannot import entity layer.",
                            },
                            {
                                group: ["@web/views/*", "@web/search/*"],
                                message:
                                    "Shared layer (ui/) cannot import widget layer.",
                            },
                            {
                                group: ["@web/webclient/*"],
                                message: "Shared layer (ui/) cannot import page layer.",
                            },
                            {
                                group: ["@web/fields/*"],
                                message:
                                    "Shared layer (ui/) cannot import feature layer.",
                            },
                            EXTENSIONLESS_RELATIVE_IMPORT,
                        ],
                    },
                ],
            },
        },
        // ── Shared layer: components/ ─────────────────────────────────────────
        {
            files: ["**/web/static/src/components/**/*.js"],
            rules: {
                "no-restricted-imports": [
                    "error",
                    {
                        patterns: [
                            {
                                group: ["@web/model/*"],
                                message:
                                    "Presentational components take their data as props; reaching into model/ binds them to the datapoint instead of the values they render.",
                            },
                            {
                                group: ["@web/views/*", "@web/search/*"],
                                message:
                                    "Shared layer (components/) cannot import widget layer.",
                            },
                            {
                                group: ["@web/webclient/*"],
                                message:
                                    "Shared layer (components/) cannot import page layer.",
                            },
                            {
                                group: ["@web/fields/*"],
                                message:
                                    "Shared layer (components/) cannot import feature layer.",
                            },
                            EXTENSIONLESS_RELATIVE_IMPORT,
                        ],
                    },
                ],
            },
        },

        // =========================================================================
        // Component-lifecycle: ban this.env.services.X in web's component layer
        //
        // ``this.env.services.X`` bypasses the lifecycle-protection wrapper that
        // ``useService("X")`` installs around every method via ``_protectMethod``
        // (core/utils/hooks.js).  Without it, an in-flight promise that resolves
        // after the component unmounts will run on a destroyed component, causing
        // "this.render is not a function" or stale-state bugs that are hard to
        // reproduce.
        //
        // Bare ``env.services.X`` (no ``this``) inside registry factories and
        // command providers is intentionally NOT flagged — those are not OWL
        // components.
        //
        // Scope: web's source files only.  Other addons (POS, mail, hr_attendance)
        // have many existing call sites that need a per-module audit before this
        // rule can be widened safely.
        // =========================================================================
        {
            files: ["**/web/static/src/**/*.js"],
            rules: {
                "no-restricted-syntax": [
                    "error",
                    "PrivateIdentifier",
                    {
                        selector:
                            "CallExpression[callee.name='reactive'] > ObjectExpression > Property[kind='set']",
                        message:
                            "Pattern 4 smell: setters inside reactive({...}) conflate state with effects. Use plain reactive({foo: null}) + useEffect for side effects, or a SignalStore subclass for computation. See machine_doc_v1/STATE_MANAGEMENT.md §Pattern 4.",
                    },
                    {
                        // `toBeCloseTo(x, { digits: n })` is the Jest spelling and
                        // hoot has no such option: its matcher takes an absolute
                        // `margin` and DEFAULTS IT TO 1. So the Jest form does not
                        // tighten the comparison, it loosens it to +/-1 — which on a
                        // 0..1 quantity asserts nothing at all, and is how a bottom
                        // sheet progress test passed against a value of 0.148.
                        selector:
                            "CallExpression[callee.property.name='toBeCloseTo'] > ObjectExpression > Property[key.name=/^(digits|precision|numDigits)$/]",
                        message:
                            "hoot's toBeCloseTo takes { margin } (an absolute tolerance, default 1), not { digits }. `{ digits: n }` is silently ignored, so the assertion holds to +/-1 — vacuous for any quantity smaller than that. Spell the margin you mean.",
                    },
                    {
                        // Any receiver, not just `this`. The selector used to
                        // require a ThisExpression, which is the shape a *class*
                        // reaches a service through -- but a hook holds its
                        // component in a local (`const owner = useComponent()`) and
                        // reaches `owner.env.services.x`, the identical hazard with
                        // none of the lifecycle protection, and the gate could not
                        // see it. Within this scope that widening reports eleven
                        // sites; each now carries a disable naming its reason,
                        // which is the point: a raw service read should be a
                        // decision on the page, not an accident of spelling.
                        //
                        // A bare `env.services.x` still does not match, and must
                        // not: a registry callback is handed an `env` and has no
                        // component to protect.
                        selector:
                            "MemberExpression[property.name='services'][object.type='MemberExpression'][object.property.name='env']",
                        message:
                            "Use useService('X') instead of <holder>.env.services.X. useService adds component-lifecycle protection that prevents promise-resolution-after-destroy bugs. If you genuinely need the raw service (e.g., the dialog outlives the widget, or there is no component to protect), add `// eslint-disable-next-line no-restricted-syntax` with a comment explaining why.",
                    },
                    // (Removed 2026-05-09) The `Reactive` BC alias was dropped
                    // from `@web/core/utils/reactive` along with this rule.
                    // Attempting `import { Reactive } from "@web/core/utils/reactive"`
                    // now fails at module-load with a native "no such export"
                    // error — clearer than a lint warning, and impossible to
                    // suppress with eslint-disable.
                ],
            },
        },

        // columnize.test.js — hand-formatted HTML-fixture test with inline
        // `/* eslint-disable */` blocks placed mid-expression. Prettier mangles
        // those into INVALID JS (spurious extra `)`), so its formatter must not run
        // on this file. The fixtures are deliberately hand-aligned; leave them be.
        {
            files: ["**/html_editor/static/tests/columnize.test.js"],
            rules: {
                "prettier/prettier": "off",
            },
        },
    ];
}

/** @type {import("eslint").Linter.Config[]} */
export default makeConfig({
    modules: COMMUNITY_MODULES,
    ignores: COMMUNITY_IGNORES,
    noConsoleModules: COMMUNITY_NO_CONSOLE_MODULES,
});
