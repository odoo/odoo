const fs = require("node:fs");
const path = require("node:path");
const { fixupPluginRules, includeIgnoreFile } = require("@eslint/compat");
const js = require("@eslint/js");
const prettierConfig = require("eslint-config-prettier");
const prettier = require("eslint-plugin-prettier");
const globals = require("globals");

// The template is also used in place (test_lint), where the ignore file has not been copied.
const ignoreFile = path.join(__dirname, ".eslint-ignore");

module.exports = [
    ...(fs.existsSync(ignoreFile) ? [includeIgnoreFile(ignoreFile)] : []),
    js.configs.recommended,
    prettierConfig,
    {
        plugins: { prettier: fixupPluginRules(prettier) },
        linterOptions: {
            reportUnusedDisableDirectives: "off",
        },
        languageOptions: {
            ecmaVersion: 2022,
            sourceType: "module",
            globals: {
                ...globals.browser,
                odoo: "readonly",
                $: "readonly",
                jQuery: "readonly",
                Chart: "readonly",
                fuzzy: "readonly",
                StackTrace: "readonly",
                luxon: "readonly",
                py: "readonly",
                FullCalendar: "readonly",
                ScrollSpy: "readonly",
                module: "readonly",
                chai: "readonly",
                describe: "readonly",
                it: "readonly",
                mocha: "readonly",
                DOMPurify: "readonly",
                Prism: "readonly",
                SIP: "readonly",

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
            "prettier/prettier": [
                "error",
                {
                    tabWidth: 4,
                    semi: true,
                    singleQuote: false,
                    printWidth: 100,
                    endOfLine: "auto",
                },
            ],
            "no-undef": "error",
            "no-restricted-globals": ["error", "event", "self"],
            "no-const-assign": ["error"],
            "no-debugger": ["error"],
            "no-dupe-class-members": ["error"],
            "no-dupe-keys": ["error"],
            "no-dupe-args": ["error"],
            "no-dupe-else-if": ["error"],
            "no-unsafe-negation": ["error"],
            "no-duplicate-imports": ["error"],
            "valid-typeof": ["error"],
            "no-unused-vars": [
                "error",
                { vars: "all", args: "none", ignoreRestSiblings: false, caughtErrors: "all" },
            ],
            curly: ["error", "all"],
            "no-restricted-syntax": [
                "error",
                "PrivateIdentifier",
                {
                    selector: "CallExpression[callee.name='useEffect'][arguments.length>1]",
                    message:
                        "Owl 3 useEffect takes a single callback: the dependency argument is silently ignored. Read the signals inside the callback, or use useOnChange.",
                },
                {
                    selector:
                        "CallExpression[callee.name='useEffect'] > :function:first-child[params.length>0]",
                    message:
                        "Owl 3 calls the useEffect callback without arguments: declared parameters are always undefined.",
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
            "no-redeclare": ["error", { builtinGlobals: false }],
            "no-inner-declarations": ["error", "functions", { blockScopedFunctions: "disallow" }],
            "no-constant-binary-expression": "off",
            "no-empty-static-block": "off",
            "no-unused-private-class-members": "off",
            "no-unassigned-vars": "off",
            "no-useless-assignment": "off",
            "preserve-caught-error": "off",
        },
    },
    {
        files: ["**/bus_worker_script.js"],
        languageOptions: { globals: globals.sharedWorker },
    },
    {
        files: ["**/tick_worker.js", "**/voip/static/src/worker/init.js"],
        languageOptions: { globals: globals.worker },
    },
    {
        files: ["**/worklets/*.js", "**/*_worklet.js"],
        languageOptions: { globals: globals.audioWorklet },
    },
    {
        files: ["**/service_worker.js"],
        languageOptions: { globals: globals.serviceworker },
    },
    ...(process.env.ODOO_ESLINT_DIFF ? require("eslint-plugin-diff").configs["flat/diff"] : []),
];
