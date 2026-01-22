/** @odoo-module */

import { browser } from "@web/core/browser/browser";
import {
    click,
    editInput,
    editSelect,
    editSelectMenu,
    getFixture,
    nextTick,
    patchWithCleanup,
} from "@web/../tests/helpers/utils";
import { createWebClient, doAction } from "@web/../tests/webclient/helpers";
import { dragenterFiles, dropFiles } from "@web/../tests/legacy/utils";
import { registry } from "@web/core/registry";
import { makeFakeNotificationService } from "@web/../tests/helpers/mock_services";
import { ImportDataProgress } from "../src/import_data_progress/import_data_progress";
import { ImportAction } from "../src/import_action/import_action";
import { ImportBlockUI } from "../src/import_block_ui";
import { useEffect } from "@odoo/owl";
import { redirect } from "@web/core/utils/urls";

const serviceRegistry = registry.category("services");

// -----------------------------------------------------------------------------
//#region Helpers
// -----------------------------------------------------------------------------

let serverData;
let target;
let totalRows;

function registerFakeHTTPService(validate = (route, params) => {}) {
    const fakeHTTPService = {
        start() {
            return {
                post: (route, params) => {
                    validate(route, params);
                    const file = {
                        id: 10,
                        name: params.ufile[0].name,
                        mimetype: "text/plain",
                    };
                    return JSON.stringify([file]);
                },
            };
        },
    };
    serviceRegistry.add("http", fakeHTTPService);
}

function getFieldsTree(serverData) {
    const fields = Object.entries(serverData.models.partner.fields);
    fields.forEach(([k, v]) => {
        v.id = k;
        v.fields = [];
    });
    const mappedFields = fields.map((e) => e[1]);
    return mappedFields.filter((e) => ["id", "__last_update", "name"].includes(e.id) === false);
}

function getMatches(serverData, headers) {
    // basic implementation for testing purposes which matches if the first line is the
    // name of a field, or corresponds to the string value of a field from serverData
    const matches = [];
    for (const header of headers) {
        if (serverData.models.partner.fields[header]) {
            matches.push([header]);
        }
        const serverDataIndex = Object.values(serverData.models.partner.fields).findIndex(
            (e) => e.string === header
        );
        if (serverDataIndex !== -1) {
            matches.push([Object.keys(serverData.models.partner.fields)[serverDataIndex]]);
        }
    }
    return Object.assign({}, matches);
}

async function executeImport(data, shouldWait = false) {
    const res = {
        ids: [],
    };
    const matching = data[1].filter((f) => f !== false);
    if (matching.length) {
        res.ids.push(1);
    } else {
        res.messages = [
            {
                type: "error",
                not_matching_error: true,
                message: "You must configure at least one field to import",
            },
        ];
    }
    if (data[3].skip + 1 < (data[3].has_headers ? totalRows - 1 : totalRows)) {
        res.nextrow = data[3].skip + data[3].limit;
    } else {
        res.nextrow = 0;
    }
    if (shouldWait) {
        // make sure the progress bar is shown
        await nextTick();
    }
    return res;
}

function parsePreview(opts) {
    const fakePreviewData = [
        ["Foo", "Acme Corporation", "Azure Interior", "Brandon Freeman"],
        ["Bar", "1", "1", "0"],
        ["Display name", "Azure Interior"],
    ];
    const headers = opts.has_headers && fakePreviewData.map((col) => col[0]);
    totalRows = [...fakePreviewData].sort((a, b) => (a.length > b.length ? -1 : 1))[0].length;

    return Promise.resolve({
        advanced_mode: opts.advanced,
        batch: false,
        fields: getFieldsTree(serverData),
        file_length: opts.has_headers ? totalRows - 1 : totalRows,
        header_types: false,
        headers: headers,
        matches: opts.has_headers && getMatches(serverData, headers),
        options: {
            ...opts,
            sheet: opts.sheet.length ? opts.sheet : "Template",
            sheets: ["Template", "Template 2"],
        },
        preview: opts.has_headers
            ? fakePreviewData.map((col) => col.shift() && col)
            : [...fakePreviewData],
    });
}

function customParsePreview(opts, { fields, headers, rowCount, matches, preview }) {
    totalRows = rowCount;

    return Promise.resolve({
        advanced_mode: opts.advanced,
        batch: false,
        fields: fields,
        file_length: opts.has_headers ? totalRows - 1 : totalRows,
        header_types: false,
        headers: headers,
        matches: matches,
        options: {
            ...opts,
            sheet: opts.sheet.length ? opts.sheet : "Template",
            sheets: ["Template", "Template 2"],
        },
        preview: preview,
    });
}

// since executing a real import would be difficult, this method simply returns
// some error messages to help testing the UI
function executeFailingImport(field, isMultiline, field_path = "") {
    let moreInfo = [];
    if (serverData.models.partner.fields[field].type === "selection") {
        moreInfo = serverData.models.partner.fields[field].selection;
    }
    return {
        ids: false,
        messages: isMultiline
            ? [
                  {
                      field,
                      field_name: serverData.models.partner.fields[field].string,
                      field_path,
                      message: "Invalid value",
                      moreInfo,
                      record: 0,
                      rows: { from: 0, to: 0 },
                      value: "Invalid value",
                      priority: "info",
                  },
                  {
                      field,
                      field_name: serverData.models.partner.fields[field].string,
                      field_path,
                      message: "Duplicate value",
                      moreInfo,
                      record: 0,
                      rows: { from: 1, to: 1 },
                      priority: "error",
                  },
                  {
                      field,
                      field_name: serverData.models.partner.fields[field].string,
                      field_path,
                      message: "Wrong values",
                      moreInfo,
                      record: 0,
                      rows: { from: 2, to: 3 },
                      priority: "warning",
                  },
                  {
                      field,
                      field_name: serverData.models.partner.fields[field].string,
                      field_path,
                      message: "Bad value here",
                      moreInfo,
                      record: 0,
                      rows: { from: 4, to: 4 },
                      value: "Bad value",
                      priority: "warning",
                  },
                  {
                      field,
                      field_name: serverData.models.partner.fields[field].string,
                      field_path,
                      message: "Duplicate value",
                      moreInfo,
                      record: 0,
                      rows: { from: 5, to: 5 },
                      priority: "error",
                  },
              ]
            : [
                  {
                      field,
                      field_name: serverData.models.partner.fields[field].string,
                      field_path,
                      message: "Incorrect value",
                      moreInfo,
                      record: 0,
                      rows: { from: 0, to: 0 },
                  },
              ],
        name: ["Some invalid content", "Wrong content", "Bad content"],
        nextrow: 0,
    };
}

async function createImportAction(customRouter = {}) {
    const router = {
        "/web/dataset/call_kw/partner/get_import_templates": (route, args) => Promise.resolve([]),
        "/web/dataset/call_kw/base_import.import/parse_preview": (route, args) =>
            parsePreview(args[1]),
        "/web/dataset/call_kw/base_import.import/execute_import": (route, args) =>
            executeImport(args),
        "/web/dataset/call_kw/base_import.import/create": (route, args) => Promise.resolve(11),
        "base_import.import/get_fields": (route, args) =>
            Promise.resolve(serverData.models.partner.fields),
    };

    for (const key in customRouter) {
        router["/web/dataset/call_kw/" + key] = customRouter[key];
    }

    const webClient = await createWebClient({
        serverData,
        mockRPC: function (route, { args }) {
            if (route in router) {
                return router[route](route.replace("/web/dataset/call_kw/", ""), args);
            }
        },
    });

    await doAction(webClient, 1);
}

// -----------------------------------------------------------------------------
//#endregion
// -----------------------------------------------------------------------------

// -----------------------------------------------------------------------------
// Tests
// -----------------------------------------------------------------------------

QUnit.module("Base Import Tests", (hooks) => {
    hooks.beforeEach(async () => {
        serverData = {
            actions: {
                1: {
                    name: "Import Data",
                    tag: "import",
                    target: "current",
                    type: "ir.actions.client",
                    params: {
                        active_model: "partner",
                    },
                },
            },
            models: {
                partner: {
                    fields: {
                        display_name: { string: "Display name", type: "char" },
                        foo: { string: "Foo", type: "char" },
                        bar: { string: "Bar", type: "boolean", model_name: "partner" },
                        selection: {
                            string: "Selection",
                            type: "selection",
                            selection: [
                                ["item_1", "First Item"],
                                ["item_2", "Second item"],
                            ],
                            model_name: "partner",
                        },
                        many2many_field: {
                            string: "Many2Many",
                            type: "many2many",
                            relation: "partner",
                            comodel_name: "comodel.test",
                        },
                    },
                    records: [],
                },
            },
        };
        target = getFixture();
    });

    QUnit.module("ImportAction");

    QUnit.test("Import view: UI before file upload", async function (assert) {
        const templateURL = "/myTemplateURL.xlsx";
        const secondTemplateURL = "/mySecondTemplateURL.xlsx";

        patchWithCleanup(browser.location, {
            origin: "http://example.com",
        });
        redirect("/odoo");

        await createImportAction({
            "partner/get_import_templates": (route, args) => {
                assert.step(route);
                return Promise.resolve([
                    {
                        label: "Some Import Template",
                        template: templateURL,
                    },
                    {
                        label: "Another Import Template",
                        template: secondTemplateURL,
                    }
                ]);
            },
            "base_import.import/create": (route, args) => {
                assert.step(route);
                return Promise.resolve(11);
            },
        });

        await nextTick(); // pushState is debounced
        assert.strictEqual(
            browser.location.href,
            "http://example.com/odoo/import?active_model=partner",
            "the url contains the active_model"
        );

        assert.containsOnce(target, ".o_import_action", "import view is displayed");
        assert.strictEqual(
            target.querySelectorAll(".o_nocontent_help .btn-outline-primary").length,
            2,
            "there are two import template buttons"
        )
        assert.strictEqual(
            target.querySelectorAll(".o_nocontent_help .btn-outline-primary")[0].textContent,
            " Some Import Template"
        );
        assert.strictEqual(
            target.querySelectorAll(".o_nocontent_help .btn-outline-primary")[0].href,
            window.location.origin + templateURL,
            "1st button has the right download url"
        );
        assert.strictEqual(
            target.querySelectorAll(".o_nocontent_help .btn-outline-primary")[1].textContent,
            " Another Import Template"
        );
        assert.strictEqual(
            target.querySelectorAll(".o_nocontent_help .btn-outline-primary")[1].href,
            window.location.origin + secondTemplateURL,
            "2nd button has the right download url"
        );
        assert.verifySteps(["partner/get_import_templates", "base_import.import/create"]);
        assert.containsN(
            target,
            ".o_control_panel button",
            2,
            "only two buttons are visible by default"
        );
    });

    QUnit.test("Import view: import a file with multiple sheets", async function (assert) {
        registerFakeHTTPService((route, params) => {
            assert.strictEqual(route, "/base_import/set_file");
            assert.strictEqual(
                params.ufile[0].name,
                "fake_file.xlsx",
                "file is correctly uploaded to the server"
            );
        });

        patchWithCleanup(browser, {
            setTimeout: (fn) => fn(),
        });

        await createImportAction({
            "partner/get_import_templates": (route, args) => {
                assert.step(route);
                return Promise.resolve([]);
            },
            "base_import.import/parse_preview": (route, args) => {
                assert.step(route);
                return parsePreview(args[1]);
            },
            "base_import.import/create": (route, args) => {
                assert.step(route);
                return Promise.resolve(11);
            },
        });

        // Set and trigger the change of a file for the input
        const file = new File(["fake_file"], "fake_file.xlsx", { type: "text/plain" });
        await editInput(target, ".o_control_panel_main_buttons input[type='file']", file);
        assert.verifySteps([
            "partner/get_import_templates",
            "base_import.import/create",
            "base_import.import/parse_preview",
        ]);
        assert.containsOnce(
            target,
            ".o_import_action .o_import_data_sidepanel",
            "side panel is visible"
        );
        assert.containsOnce(
            target,
            ".o_import_action .o_import_data_content",
            "content panel is visible"
        );
        assert.strictEqual(
            target.querySelector(".o_import_data_sidepanel .fst-italic.truncate").textContent,
            "fake_file",
            "filename is shown and can be truncated"
        );
        assert.strictEqual(
            target.querySelector(".o_import_data_sidepanel .fst-italic:not(.truncate)").textContent,
            ".xlsx",
            "file extension is displayed on its own"
        );
        assert.strictEqual(
            target.querySelector(".o_import_data_sidepanel [name=o_import_sheet]")
                .selectedOptions[0].textContent,
            "Template",
            "first sheet is selected by default"
        );

        assert.containsN(
            target,
            ".o_import_data_content tbody > tr",
            3,
            "recognized values are displayed in the view"
        );
        assert.strictEqual(
            target.querySelector(".o_import_data_content tr:first-child td span:first-child")
                .textContent,
            "Foo",
            "column title is shown"
        );
        assert.strictEqual(
            target.querySelector(".o_import_data_content tr:first-child td span:nth-child(2)")
                .textContent,
            "Acme Corporation",
            "first example is shown"
        );
        assert.strictEqual(
            target.querySelector(".o_import_data_content tr:first-child td span:nth-child(2)")
                .dataset.tooltipInfo,
            '{"lines":["Acme Corporation","Azure Interior","Brandon Freeman"]}',
            "tooltip contains other examples"
        );
        assert.containsNone(
            target,
            ".o_import_data_content tbody td:nth-child(3) .alert-info",
            "no comments are shown"
        );

        // Select a field already selected for another column
        await editSelectMenu(target, ".o_import_data_content .o_select_menu", "Display name");
        assert.containsN(
            target,
            ".o_import_data_content tbody td:nth-child(3) .alert-info",
            2,
            "two comments are shown"
        );
        assert.strictEqual(
            target.querySelector(".o_import_data_content tbody td:nth-child(3) .alert-info")
                .textContent,
            "This column will be concatenated in field Display name"
        );

        // Preview the second sheet
        await editSelect(target, ".o_import_data_sidepanel [name=o_import_sheet]", "Template 2");
        assert.verifySteps(
            ["base_import.import/parse_preview"],
            "changing sheet has sent a new parse_preview request"
        );
        assert.strictEqual(
            target.querySelector(".o_import_data_sidepanel [name=o_import_sheet]")
                .selectedOptions[0].textContent,
            "Template 2",
            "second sheet is now selected"
        );
        assert.containsNone(
            target,
            ".o_import_data_content tbody td:nth-child(3) .alert-info",
            "no comments are shown"
        );
    });

    QUnit.test("Import view: default import options are correctly", async function (assert) {
        registerFakeHTTPService();
        await createImportAction({
            "base_import.import/parse_preview": async (route, args) => {
                return parsePreview(args[1]);
            },
            "base_import.import/execute_import": (route, args) => {
                assert.step("execute_import");
                assert.deepEqual(
                    args[3],
                    {
                        advanced: true,
                        date_format: "",
                        datetime_format: "",
                        encoding: "",
                        fallback_values: {},
                        float_decimal_separator: ".",
                        float_thousand_separator: ",",
                        has_headers: true,
                        import_set_empty_fields: [],
                        import_skip_records: [],
                        keep_matches: false,
                        limit: 2000,
                        name_create_enabled_fields: {},
                        quoting: '"',
                        separator: "",
                        sheet: "Template",
                        sheets: ["Template", "Template 2"],
                        skip: 0,
                        tracking_disable: true,
                    },
                    "options are defaulted as expected"
                );
                return executeImport(args);
            },
        });

        // Set and trigger the change of a file for the input
        const file = new File(["fake_file"], "fake_file.xls", { type: "text/plain" });
        await editInput(target, ".o_control_panel_main_buttons input[type='file']", file);
        await click(target.querySelector(".o_control_panel_main_buttons button:first-child"));
        assert.verifySteps(["execute_import"]);
    });

    QUnit.test("Import view: import a CSV file with one sheet", async function (assert) {
        registerFakeHTTPService((route, params) => {
            assert.strictEqual(route, "/base_import/set_file");
            assert.strictEqual(
                params.ufile[0].name,
                "fake_file.csv",
                "file is correctly uploaded to the server"
            );
        });
        await createImportAction();

        // Set and trigger the change of a file for the input
        const file = new File(["fake_file"], "fake_file.csv", { type: "text/plain" });
        await editInput(target, ".o_control_panel_main_buttons input[type='file']", file);
        assert.containsOnce(
            target,
            ".o_import_data_sidepanel .o_import_formatting",
            "formatting options are present in the side panel"
        );
        assert.containsOnce(
            target,
            ".o_import_action .o_import_data_content",
            "content panel is visible"
        );
    });

    QUnit.test("Import view: drag-and-drop file support", async function (assert) {
        registerFakeHTTPService((route, params) => {
            assert.strictEqual(route, "/base_import/set_file");
            assert.strictEqual(
                params.ufile[0].name,
                "fake_file.csv",
                "file is correctly uploaded to the server"
            );
        });
        await createImportAction();
        const file = new File(["fake_file"], "fake_file.csv", {
            type: "text/plain"
        });
        await dragenterFiles(".o_import_action", [file]);
        await dropFiles(".o-Dropzone", [file]);
        await nextTick();
        assert.containsOnce(
            target,
            ".o_import_action .o_import_data_content",
            "content panel is visible"
        );
    });

    QUnit.test("Import view: import a CSV file with uppercase extension", async function (assert) {
        registerFakeHTTPService((route, params) => {
            assert.strictEqual(route, "/base_import/set_file");
            assert.strictEqual(
                params.ufile[0].name,
                "fake_file.CSV",
                "file with uppercase .CSV extension is correctly uploaded to the server"
            );
        });
        await createImportAction();

        // Simulate uploading a .CSV file (uppercase extension)
        const file = new File(["fake_file"], "fake_file.CSV", { type: "text/plain" });
        await editInput(target, ".o_control_panel_main_buttons input[type='file'].d-none", file);

        assert.containsOnce(
            target,
            ".o_import_data_sidepanel .o_import_formatting",
            "formatting options are shown for uppercase extention .CSV file"
        );
    });

    QUnit.test("Import view: additional options in debug", async function (assert) {
        patchWithCleanup(odoo, { debug: true });
        registerFakeHTTPService();

        await createImportAction({
            "base_import.import/parse_preview": (route, args) => {
                assert.strictEqual(
                    args[1].advanced,
                    true,
                    "in debug, advanced_mode is set in parse_preview"
                );
                return parsePreview(args[1]);
            },
        });

        // Set and trigger the change of a file for the input
        const file = new File(["fake_file"], "fake_file.csv", { type: "text/plain" });
        await editInput(target, ".o_control_panel_main_buttons input[type='file']", file);

        await nextTick();
        assert.containsOnce(
            target,
            ".o_import_data_sidepanel .o_import_debug_options",
            "additional options are present in the side panel in debug mode"
        );
    });

    QUnit.test("batched import doesn't exit when a failure occurs", async function (assert) {
        serverData.actions[2] = {
            id: 2,
            name: "Partner List",
            res_model: "partner",
            type: "ir.actions.act_window",
            domain: "[]",
            views: [[false, "list"]],
        };

        serverData.views = {
            "partner,false,list": `<list><field name="name"/></list>`,
            "partner,false,search": "<search></search>",
        };

        registerFakeHTTPService();

        patchWithCleanup(ImportAction.prototype, {
            get isBatched() {
                // make sure the UI displays the batched import options
                return true;
            },
        });

        const notificationMock = (message) => {
            assert.step(message);
            return () => {};
        };
        registry
            .category("services")
            .add("notification", makeFakeNotificationService(notificationMock), {
                force: true,
            });

        patchWithCleanup(browser, {
            setTimeout: (fn) => fn(),
        });

        const steps = [
            (args) => executeImport(args, true),
            (args) => executeFailingImport(args[1][0]),
        ];

        const webClient = await createWebClient({
            serverData,
            mockRPC: function (route, args) {
                switch (route) {
                    case "/web/dataset/call_kw/partner/get_import_templates":
                        return Promise.resolve([]);

                    case "/web/dataset/call_kw/base_import.import/parse_preview":
                        return parsePreview(args.args[1]);

                    case "/web/dataset/call_kw/base_import.import/execute_import":
                        return steps.shift()(args.args);

                    case "/web/dataset/call_kw/base_import.import/create":
                        return Promise.resolve(11);

                    case "base_import.import/get_fields":
                        return Promise.resolve(serverData.models.partner.fields);

                    case "/web/action/load":
                        assert.step(`/web/action/load id=${args.action_id}`);
                }
            },
        });

        await doAction(webClient, 2);
        await doAction(webClient, 1);

        assert.verifySteps(["/web/action/load id=2", "/web/action/load id=1"]);

        const file = new File(["fake_file"], "fake_file.xlsx", { type: "text/plain" });
        await editInput(target, ".o_control_panel_main_buttons input[type='file']", file);
        await editInput(target, "input#o_import_batch_limit", 1);

        const importButton = Array.from(
            target.querySelectorAll(".o_control_panel_main_buttons button")
        ).find((e) => e.textContent === "Import");

        await click(importButton);
        await nextTick();

        assert.strictEqual(
            target.querySelector(".alert-danger")?.textContent,
            "The file contains blocking errors (see below)"
        );

        assert.strictEqual(
            target.querySelector(".o_import_report.alert-danger")?.textContent,
            "Incorrect value"
        );

        assert.verifySteps([]); // This makes sure that we don't exit the import action
    });

    QUnit.test(
        "Import view: execute import with option 'use first row as headers'",
        async function (assert) {
            registerFakeHTTPService();
            const notificationMock = (message) => {
                assert.step(message);
                return () => {};
            };
            registry
                .category("services")
                .add("notification", makeFakeNotificationService(notificationMock), {
                    force: true,
                });

            patchWithCleanup(browser, {
                setTimeout: (fn) => fn(),
            });

            await createImportAction({
                "base_import.import/parse_preview": async (route, args) => {
                    assert.step(route);
                    return parsePreview(args[1]);
                },
                "base_import.import/execute_import": (route, args) => {
                    assert.step(route);
                    return executeImport(args);
                },
            });

            // Set and trigger the change of a file for the input
            const file = new File(["fake_file"], "fake_file.xls", { type: "text/plain" });
            await editInput(target, ".o_control_panel_main_buttons input[type='file']", file);
            assert.strictEqual(
                target.querySelector(".o_import_data_sidepanel input[type=checkbox]").checked,
                true,
                "by default, the checkbox is enabled"
            );
            assert.verifySteps(["base_import.import/parse_preview"]);
            assert.strictEqual(
                target.querySelector(".o_import_data_content tr:first-child td span:first-child")
                    .textContent,
                "Foo",
                "first row is used as column title"
            );
            assert.strictEqual(
                target.querySelector(".o_import_data_content .o_select_menu").textContent,
                "Foo",
                "as the column header could match with a database field, it is selected by default"
            );

            await click(target.querySelector(".o_import_data_sidepanel input[type=checkbox]"));
            assert.verifySteps(["base_import.import/parse_preview"]);
            assert.strictEqual(
                target.querySelector(".o_import_data_content tr:first-child td span:first-child")
                    .textContent,
                "Foo, Acme Corporation, Azure Interior, Brandon Freeman",
                "column title is shown as a list of rows elements"
            );
            assert.strictEqual(
                target.querySelector(".o_import_data_content .o_select_menu").textContent,
                "To import, select a field...",
                "as the column couldn't match with the database, user must make a choice"
            );

            await click(target.querySelector(".o_control_panel_main_buttons button:first-child"));
            assert.containsNone(
                target,
                ".o_notification_body",
                "should not display a notification"
            );
            assert.verifySteps(["base_import.import/execute_import"]);
            assert.containsOnce(
                target,
                ".o_import_data_content .alert-info",
                "if no fields were selected to match, the import fails with a message"
            );
            assert.containsOnce(
                target,
                ".o_import_data_content .alert-danger",
                "an error is also displayed"
            );
            assert.strictEqual(
                target.querySelector(".o_import_data_content .alert-danger").textContent,
                "You must configure at least one field to import"
            );

            await editSelectMenu(target, ".o_import_data_content .o_select_menu", "Display name");
            await click(target.querySelector(".o_control_panel_main_buttons button:first-child"));
            assert.verifySteps([
                "base_import.import/execute_import",
                "1 records successfully imported",
            ]);
        }
    );

    QUnit.test("Import view: import data that don't match (selection)", async function (assert) {
        serverData.models.partner.fields.selection.required = true;
        let shouldFail = true;

        registerFakeHTTPService();
        patchWithCleanup(browser, {
            setTimeout: (fn) => fn(),
        });

        await createImportAction({
            "base_import.import/execute_import": (route, args) => {
                if (shouldFail) {
                    shouldFail = false;
                    return executeFailingImport(args[1][0]);
                }
                assert.deepEqual(
                    args[3].fallback_values,
                    {
                        selection: {
                            fallback_value: "item_2",
                            field_model: "partner",
                            field_type: "selection",
                        },
                    },
                    "selected fallback value has been given to the request"
                );
                return executeImport(args);
            },
        });

        // Set and trigger the change of a file for the input
        const file = new File(["fake_file"], "fake_file.xlsx", { type: "text/plain" });
        await editInput(target, ".o_control_panel_main_buttons input[type='file']", file);
        // For this test, we force the display of an error message if this field is set
        await editSelectMenu(target, ".o_import_data_content .o_select_menu", "Selection");
        await click(target.querySelector(".o_control_panel_main_buttons button:nth-child(2)"));
        assert.strictEqual(
            target.querySelector(".o_import_data_content .alert-danger").textContent,
            "The file contains blocking errors (see below)",
            "a message is shown if the import was blocked"
        );
        assert.strictEqual(
            target.querySelector(".o_import_report p").textContent,
            "Incorrect value",
            "the message is displayed in the view"
        );
        assert.containsOnce(
            target,
            ".o_import_field_selection",
            "an action can be set when the column cannot match a field"
        );
        assert.strictEqual(
            target.querySelector(".o_import_field_selection select").textContent,
            "Prevent importSet to: First ItemSet to: Second item",
            "'skip' option is not available, since the field is required"
        );
        assert.strictEqual(
            target.querySelector(".o_import_field_selection select").selectedOptions[0].textContent,
            "Prevent import",
            "prevent option is selected by default"
        );
        editSelect(target, ".o_import_field_selection select", "item_2");
        await click(target.querySelector(".o_control_panel_main_buttons button:nth-child(2)"));
        assert.strictEqual(
            target.querySelector(".o_import_data_content .alert-info").textContent,
            "Everything seems valid.",
            "import is now successful"
        );
        assert.containsOnce(
            target,
            ".o_import_field_selection",
            "options are still present to change the action to do when the column don't match"
        );
    });

    QUnit.test("Import view: import data that don't match (boolean)", async function (assert) {
        let shouldFail = true;

        registerFakeHTTPService();
        patchWithCleanup(browser, {
            setTimeout: (fn) => fn(),
        });

        await createImportAction({
            "base_import.import/execute_import": (route, args) => {
                if (shouldFail) {
                    shouldFail = false;
                    return executeFailingImport(args[1][0]);
                }
                assert.deepEqual(
                    args[3].fallback_values,
                    {
                        bar: {
                            fallback_value: "false",
                            field_model: "partner",
                            field_type: "boolean",
                        },
                    },
                    "selected fallback value has been given to the request"
                );
                return executeImport(args);
            },
        });

        // Set and trigger the change of a file for the input
        const file = new File(["fake_file"], "fake_file.xlsx", { type: "text/plain" });
        await editInput(target, ".o_control_panel_main_buttons input[type='file']", file);
        // For this test, we force the display of an error message if this field is set
        await editSelectMenu(target, ".o_import_data_content .o_select_menu", "Bar");
        await click(target.querySelector(".o_control_panel_main_buttons button:nth-child(2)"));
        assert.strictEqual(
            target.querySelector(".o_import_data_content .alert-danger").textContent,
            "The file contains blocking errors (see below)",
            "a message is shown if the import was blocked"
        );
        assert.strictEqual(
            target.querySelector(".o_import_field_boolean select").textContent,
            "Prevent importSet to: FalseSet to: TrueSkip record",
            "options are 'prevent', choose a default boolean value or 'skip'"
        );
        editSelect(target, ".o_import_field_boolean select", "false");
        await click(target.querySelector(".o_control_panel_main_buttons button:nth-child(2)"));
        assert.strictEqual(
            target.querySelector(".o_import_data_content .alert-info").textContent,
            "Everything seems valid.",
            "import is now successful"
        );
    });

    QUnit.test("Import view: import data that don't match (many2many)", async function (assert) {
        let executeCount = 0;

        registerFakeHTTPService();
        patchWithCleanup(browser, {
            setTimeout: (fn) => fn(),
        });

        await createImportAction({
            "base_import.import/execute_import": (route, args) => {
                executeCount++;
                if (executeCount === 1) {
                    return executeFailingImport(args[1][0]);
                }
                if (executeCount === 2) {
                    assert.deepEqual(
                        args[3].name_create_enabled_fields,
                        {
                            many2many_field: true,
                        },
                        "selected fallback value has been given to the request"
                    );
                } else {
                    assert.deepEqual(
                        args[3].name_create_enabled_fields,
                        {},
                        "selected fallback value has been given to the request"
                    );
                    assert.deepEqual(
                        args[3].import_skip_records,
                        ["many2many_field"],
                        "selected fallback value has been given to the request"
                    );
                }
                return executeImport(args);
            },
        });

        // Set and trigger the change of a file for the input
        const file = new File(["fake_file"], "fake_file.xlsx", { type: "text/plain" });
        await editInput(target, ".o_control_panel_main_buttons input[type='file']", file);
        // For this test, we force the display of an error message if this field is set
        await editSelectMenu(target, ".o_import_data_content .o_select_menu", "Many2Many");
        await click(target.querySelector(".o_control_panel_main_buttons button:nth-child(2)"));
        assert.strictEqual(
            target.querySelector(".o_import_data_content .alert-danger").textContent,
            "The file contains blocking errors (see below)",
            "a message is shown if the import was blocked"
        );
        assert.strictEqual(
            target.querySelector(".o_import_field_many2many select").textContent,
            "Prevent importSet value as emptySkip recordCreate new values",
            "options are 'prevent', choose a default boolean value or 'skip'"
        );
        editSelect(target, ".o_import_field_many2many select", "name_create_enabled_fields");
        await click(target.querySelector(".o_control_panel_main_buttons button:nth-child(2)"));
        assert.strictEqual(
            target.querySelector(".o_import_data_content .alert-info").textContent,
            "Everything seems valid.",
            "import is now successful"
        );
        editSelect(target, ".o_import_field_many2many select", "import_skip_records");
        await click(target.querySelector(".o_control_panel_main_buttons button:nth-child(2)"));
        assert.strictEqual(
            target.querySelector(".o_import_data_content .alert-info").textContent,
            "Everything seems valid.",
            "import is still successful"
        );
    });

    QUnit.test("Import view: import messages are grouped and sorted", async function (assert) {
        const fakeHTTPService = {
            start() {
                return {
                    post: (route, params) => {
                        const file = {
                            id: 10,
                            name: params.ufile[0].name,
                            mimetype: "text/plain",
                        };
                        return JSON.stringify([file]);
                    },
                };
            },
        };
        serviceRegistry.add("http", fakeHTTPService);

        patchWithCleanup(browser, {
            setTimeout: (fn) => fn(),
        });

        const webClient = await createWebClient({
            serverData,
            mockRPC: function (route, { args }) {
                if (route === "/web/dataset/call_kw/partner/get_import_templates") {
                    return Promise.resolve([]);
                }
                if (route === "/web/dataset/call_kw/base_import.import/parse_preview") {
                    return parsePreview(args[1]);
                }
                if (route === "/web/dataset/call_kw/base_import.import/get_fields") {
                    assert.step(route);
                    return Promise.resolve(serverData.models.partner.fields);
                }
                if (route === "/web/dataset/call_kw/base_import.import/execute_import") {
                    return executeFailingImport(args[1][0], true);
                }
                if (route === "/web/dataset/call_kw/base_import.import/create") {
                    return Promise.resolve(11);
                }
            },
        });

        await doAction(webClient, 1);

        // Set and trigger the change of a file for the input
        const file = new File(["fake_file"], "fake_file.xlsx", { type: "text/plain" });
        await editInput(target, ".o_control_panel_main_buttons input[type='file']", file);
        await click(target.querySelector(".o_control_panel_main_buttons button:nth-child(1)"));
        assert.strictEqual(
            target.querySelector(".o_import_data_content .alert-danger").textContent,
            "The file contains blocking errors (see below)",
            "a message is shown if the import was blocked"
        );
        // Check that errors have been sorted and grouped
        assert.strictEqual(
            target.querySelector(".o_import_report p").textContent.trim().toLowerCase(),
            "multiple errors occurred  in field foo:"
        );
        assert.strictEqual(
            target.querySelector(".o_import_report li:first-child").textContent.trim(),
            "Duplicate value at multiple rows"
        );
        assert.strictEqual(
            target.querySelector(".o_import_report li:nth-child(2)").textContent.trim(),
            "Wrong values at multiple rows"
        );
        assert.strictEqual(
            target.querySelector(".o_import_report li:nth-child(3)").textContent.trim(),
            "Bad value at row 5"
        );
        assert.containsN(target, ".o_import_report li", 3, "only 3 errors are visible by default");
        assert.strictEqual(
            target.querySelector(".o_import_report_count").textContent.trim(),
            "1 more"
        );

        await click(target, ".o_import_report_count");
        assert.strictEqual(
            target.querySelector(".o_import_report_count + li").textContent.trim(),
            "Invalid value at row 1 (Some invalid content)"
        );
    });

    QUnit.test("Import view: test import in batches", async function (assert) {
        let executeImportCount = 0;
        registerFakeHTTPService();

        patchWithCleanup(ImportAction.prototype, {
            get isBatched() {
                // make sure the UI displays the batched import options
                return true;
            },
        });

        await createImportAction({
            "base_import.import/execute_import": (route, args) => {
                assert.deepEqual(
                    args[1],
                    ["foo", "bar", "display_name"],
                    "param contains the list of matching fields"
                );
                assert.deepEqual(
                    args[2],
                    ["foo", "bar", "display name"],
                    "param contains the list of associated columns"
                );
                assert.strictEqual(
                    args[3].limit,
                    1,
                    "limit option is equal to the value set in the view"
                );
                assert.strictEqual(
                    args[3].skip,
                    executeImportCount * args[3].limit,
                    "skip option increments at each import"
                );
                executeImportCount++;
                return executeImport(args);
            },
        });

        // Set and trigger the change of a file for the input
        const file = new File(["fake_file"], "fake_file.xls", { type: "text/plain" });
        await editInput(target, ".o_control_panel_main_buttons input[type='file']", file);
        assert.strictEqual(
            target.querySelector("input#o_import_batch_limit").value,
            "2000",
            "by default, the batch limit is set to 2000 rows"
        );
        assert.strictEqual(
            target.querySelector("input#o_import_row_start").value,
            "1",
            "by default, the import starts at line 1"
        );

        await editInput(target, "input#o_import_batch_limit", 1);
        await click(target.querySelector(".o_control_panel_main_buttons button:nth-child(2)"));
        assert.strictEqual(
            target.querySelector(".o_import_data_content .alert-info").textContent,
            "Everything seems valid.",
            "a message is shown if the import test was successfull"
        );
        assert.strictEqual(executeImportCount, 3, "execute_import was called 3 times");
    });

    QUnit.test("Import view: execute and pause import in batches", async function (assert) {
        registerFakeHTTPService();

        patchWithCleanup(ImportAction.prototype, {
            get isBatched() {
                // make sure the UI displays the batched import options
                return true;
            },
        });

        patchWithCleanup(ImportBlockUI.prototype, {
            setup() {
                super.setup();
                if (this.props.message === "Importing") {
                    assert.step("Block UI received the right text");
                }
            },
        });

        patchWithCleanup(ImportDataProgress.prototype, {
            setup() {
                super.setup();
                useEffect(
                    () => {
                        if (this.props.importProgress.step === 1) {
                            // Trigger a pause at this step to resume later from the view
                            assert.step("pause triggered during step 2");
                            this.interrupt();
                        }
                    },
                    () => [this.props.importProgress.step]
                );

                assert.strictEqual(
                    this.props.totalSteps,
                    3,
                    "progress bar receives the number of steps"
                );
                assert.deepEqual(
                    this.props.importProgress,
                    {
                        value: 0,
                        step: 1,
                    },
                    "progress status has been given to the progress bar"
                );
            },
        });

        await createImportAction({
            "base_import.import/execute_import": (route, args) => executeImport(args, true),
        });

        // Set and trigger the change of a file for the input
        const file = new File(["fake_file"], "fake_file.xls", { type: "text/plain" });
        await editInput(target, ".o_control_panel_main_buttons input[type='file']", file);
        await editInput(target, "input#o_import_batch_limit", 1);
        await click(target.querySelector(".o_control_panel_main_buttons button:first-child"));
        // Since a nextTick is added to each batch, we must wait twice before the end of the second batch
        await nextTick();
        await nextTick();
        assert.verifySteps(["Block UI received the right text", "pause triggered during step 2"]);
        assert.containsOnce(
            target,
            ".o_import_data_content div .alert-warning",
            "a message is shown to indicate the user to resume from the third row"
        );
        assert.strictEqual(
            target.querySelector(".o_import_data_content .alert-warning b:first-child").textContent,
            "Click 'Resume' to proceed with the import, resuming at line 2.",
            "a message is shown to indicate the user to resume from the third row"
        );
        assert.strictEqual(
            target.querySelector(".o_control_panel_main_buttons button:first-child").textContent,
            "Resume",
            "button contains the right text"
        );
        assert.strictEqual(
            target.querySelector("input#o_import_row_start").value,
            "2",
            "the import will resume at line 2"
        );
        assert.strictEqual(
            target.querySelector(".o_notification_body").textContent,
            "1 records successfully imported",
            "display a notification with the quantity of imported values"
        );
    });

    QUnit.test("Import view: test and pause import in batches", async function (assert) {
        registerFakeHTTPService();

        patchWithCleanup(ImportAction.prototype, {
            get isBatched() {
                // make sure the UI displays the batched import options
                return true;
            },
        });

        patchWithCleanup(ImportBlockUI.prototype, {
            setup() {
                super.setup();
                if (this.props.message === "Testing") {
                    assert.step("Block UI received the right text");
                }
            },
        });

        patchWithCleanup(ImportDataProgress.prototype, {
            setup() {
                super.setup();
                useEffect(
                    () => {
                        if (this.props.importProgress.step === 1) {
                            // Trigger a pause at this step to resume later from the view
                            assert.step("pause triggered during step 2");
                            this.interrupt();
                        }
                    },
                    () => [this.props.importProgress.step]
                );

                assert.strictEqual(
                    this.props.totalSteps,
                    3,
                    "progress bar receives the number of steps"
                );
                assert.deepEqual(
                    this.props.importProgress,
                    {
                        value: 0,
                        step: 1,
                    },
                    "progress status has been given to the progress bar"
                );
            },
        });

        await createImportAction({
            "base_import.import/execute_import": (route, args) => executeImport(args, true),
        });

        // Set and trigger the change of a file for the input
        const file = new File(["fake_file"], "fake_file.xls", { type: "text/plain" });
        await editInput(target, ".o_control_panel_main_buttons input[type='file']", file);
        await editInput(target, "input#o_import_batch_limit", 1);
        await click(target.querySelector(".o_control_panel_main_buttons button:nth-child(2)"));
        // Since a nextTick is added to each batch, we must wait twice before the end of the second batch
        await nextTick();
        await nextTick();
        assert.verifySteps(["Block UI received the right text", "pause triggered during step 2"]);
        assert.strictEqual(
            target.querySelector(".o_import_data_content .alert-info").textContent,
            "Everything seems valid."
        );
        assert.strictEqual(
            target.querySelector(".o_control_panel_main_buttons button:first-child").textContent,
            "Import",
            "after testing, 'Resume' text is not shown"
        );
        assert.strictEqual(
            target.querySelector("input#o_import_row_start").value,
            "1",
            "the import will resume at line 1"
        );
    });

    QUnit.test("Import view: test in batches then reset starting row", async function (assert) {
        registerFakeHTTPService();

        patchWithCleanup(ImportAction.prototype, {
            get isBatched() {
                return true;
            },
        });

        await createImportAction({
            "base_import.import/execute_import": (route, args) => executeImport(args, true),
        });

        const file = new File(["fake_file"], "fake_file.xls", { type: "text/plain" });
        await editInput(target, ".o_control_panel_main_buttons input[type='file']", file);
        await editInput(target, "input#o_import_batch_limit", 1);

        // click on the test button
        await click(target.querySelector(".o_control_panel_main_buttons button:nth-child(2)"));
        await nextTick();
        assert.strictEqual(target.querySelector("input#o_import_row_start").value, "2");
        await nextTick();
        assert.strictEqual(target.querySelector("input#o_import_row_start").value, "3");

        // The import is now done
        await nextTick();
        assert.strictEqual(
            target.querySelector(".o_import_data_content .alert-info").textContent,
            "Everything seems valid."
        );
        assert.strictEqual(
            target.querySelector("input#o_import_row_start").value,
            "1",
            "the actual import will start at line 1 after testing"
        );
    });

    QUnit.test(
        "Import view: relational fields correctly mapped on preview",
        async function (assert) {
            assert.expect(4);

            registerFakeHTTPService();
            await createImportAction({
                "base_import.import/parse_preview": async (route, args) => {
                    return customParsePreview(args[1], {
                        fields: [
                            { id: "id", name: "id", string: "External ID", fields: [], type: "id" },
                            {
                                id: "display_name",
                                name: "display_name",
                                string: "Display Name",
                                fields: [],
                                type: "id",
                            },
                            {
                                id: "many2many_field",
                                name: "many2many_field",
                                string: "Many2Many",
                                fields: [
                                    {
                                        id: "id",
                                        name: "id",
                                        string: "External ID",
                                        fields: [],
                                        type: "id",
                                    },
                                ],
                                type: "id",
                            },
                        ],
                        headers: ["id", "display_name", "many2many_field/id"],
                        rowCount: 5,
                        matches: {
                            0: ["id"],
                            1: ["display_name"],
                            2: ["many2many_field", "id"],
                        },
                        preview: [
                            ["0", "1", "2"],
                            ["Name 1", "Name 2", "Name 3"],
                            ["", "1", "2"],
                        ],
                    });
                },
                "base_import.import/execute_import": (route, args) => {
                    assert.deepEqual(
                        args[1],
                        ["id", "display_name", "many2many_field/id"],
                        "The proper arguments are given for the import"
                    );
                    assert.deepEqual(
                        args[2],
                        ["id", "display_name", "many2many_field/id"],
                        "The proper arguments are given for the import"
                    );
                    return executeImport(args);
                },
            });

            // Set and trigger the change of a file for the input
            const file = new File(["fake_file"], "fake_file.xls", { type: "text/plain" });
            await editInput(target, ".o_control_panel_main_buttons input[type='file']", file);

            assert.strictEqual(
                target.querySelector(
                    "tr:nth-child(3) .o_import_file_column_cell span.text-truncate"
                ).innerText,
                "many2many_field/id",
                "The third row should be the relational field"
            );

            assert.strictEqual(
                target.querySelector("tr:nth-child(3) .o_select_menu_toggler_slot span").innerText,
                "Many2Many / External ID",
                "The relational field should be selected by default and the name should be the full path."
            );

            await click(target.querySelector(".o_control_panel_main_buttons button:first-child"));
        }
    );

    QUnit.test("Import view: batch import relational fields", async function (assert) {
        let executeImportCount = 0;
        registerFakeHTTPService();

        patchWithCleanup(ImportAction.prototype, {
            get isBatched() {
                // Make sure the UI displays the batched import options
                return true;
            },
        });

        await createImportAction({
            "base_import.import/parse_preview": (route, args) => {
                // Parse a file where all rows besides the first are used for relational data
                return customParsePreview(args[1], {
                    fields: [
                        { id: "id", name: "id", string: "External ID", fields: [], type: "id" },
                        {
                            id: "display_name",
                            name: "display_name",
                            string: "Display Name",
                            fields: [],
                            type: "id",
                        },
                        {
                            id: "many2many_field",
                            name: "many2many_field",
                            string: "Many2Many",
                            fields: [
                                {
                                    id: "id",
                                    name: "id",
                                    string: "External ID",
                                    fields: [],
                                    type: "id",
                                },
                            ],
                            type: "id",
                        },
                    ],
                    headers: ["id", "display_name", "many2many_field/id"],
                    rowCount: 6,
                    matches: {
                        0: ["id"],
                        1: ["display_name"],
                        2: ["many2many_field", "id"],
                    },
                    preview: [
                        ["1"],
                        ["Record Name"],
                        ["1", "2", "3", "4", "5"],
                    ],
                });
            },
            "base_import.import/execute_import": async (route, args) => {
                ++executeImportCount;
                const res = await executeImport(args);
                // Import batch limit doesn't apply to relational fields, so set `nextrow`
                // to 0 to indicate all rows were imported on first call
                res.nextrow = 0;
                return res;
            },
        });

        const file = new File(["fake_file"], "fake_file.xlsx", { type: "text/plain" });
        await editInput(target, ".o_control_panel_main_buttons input[type='file']", file);

        // Set batch limit to 1
        await editInput(target, "input#o_import_batch_limit", 1);

        // Start test
        await click(target.querySelector(".o_control_panel_main_buttons button:nth-child(2)"));

        assert.strictEqual(
            target.querySelector(".o_import_data_content .alert-info").textContent,
            "Everything seems valid.",
            "A message should indicate the import test was successful"
        );
        assert.strictEqual(executeImportCount, 1, "Execute import should finish in 1 step");
    });

    QUnit.test("Import view: import errors with relational fields", async function (assert) {
        registerFakeHTTPService();
        patchWithCleanup(browser, {
            setTimeout: (fn) => fn(),
        });

        await createImportAction({
            "base_import.import/parse_preview": async (route, args) => {
                return customParsePreview(args[1], {
                    fields: [
                        { id: "id", name: "id", string: "External ID", fields: [], type: "id" },
                        {
                            id: "display_name",
                            name: "display_name",
                            string: "Display Name",
                            fields: [],
                            type: "id",
                        },
                        {
                            id: "many2many_field",
                            name: "many2many_field",
                            string: "Many2Many",
                            fields: [
                                {
                                    id: "id",
                                    name: "id",
                                    string: "External ID",
                                    fields: [],
                                    type: "id",
                                },
                            ],
                            type: "id",
                        },
                    ],
                    headers: ["id", "display_name", "many2many_field/id"],
                    rowCount: 5,
                    matches: {
                        0: ["id"],
                        1: ["display_name"],
                        2: ["many2many_field", "id"],
                    },
                    preview: [
                        ["0", "1", "2"],
                        ["Name 1", "Name 2", "Name 3"],
                        ["", "1", "2"],
                    ],
                });
            },
            "base_import.import/execute_import": (route, args) => {
                return executeFailingImport(args[1][0], true, ["many2many_field", "id"]);
            },
        });

        // Set and trigger the change of a file for the input
        const file = new File(["fake_file"], "fake_file.xlsx", { type: "text/plain" });
        await editInput(target, ".o_control_panel_main_buttons input[type='file']", file);
        // For this test, we force the display of an error message if this field is set
        await editSelectMenu(target, ".o_import_data_content .o_select_menu", "Many2Many");
        await click(target.querySelector(".o_control_panel_main_buttons button:nth-child(2)"));

        assert.strictEqual(
            target.querySelector(".o_import_data_content .alert-danger").textContent,
            "The file contains blocking errors (see below)",
            "A message is shown if the import was blocked"
        );

        assert.strictEqual(
            target.querySelector("tr:nth-child(3) .o_import_file_column_cell span.text-truncate")
                .innerText,
            "many2many_field/id",
            "The third row should be the relational field"
        );

        assert.strictEqual(
            target.querySelector("tr:nth-child(3) .o_select_menu_toggler_slot span").innerText,
            "Many2Many / External ID",
            "The relational field is properly mapped"
        );

        assert.containsOnce(
            target,
            "tr:nth-child(3) .o_import_report.alert",
            "The relational field should have error messages on his row"
        );

        assert.strictEqual(
            target.querySelector("tr:nth-child(3) .o_import_report.alert p b").innerText,
            "Many2Many / External ID",
            "The error should contain the full path of the relational field"
        );
    });

    QUnit.test("Import view: date format should be converted to strftime", async function (assert) {
        assert.expect(5);
        registerFakeHTTPService();
        let parseCount = 0;
        await createImportAction({
            "base_import.import/parse_preview": async (route, args) => {
                parseCount++;
                const response = await parsePreview(args[1]);
                if (parseCount === 2) {
                    assert.strictEqual(
                        response.options.date_format,
                        "%Y%m%d",
                        "server sends back a strftime formatted date"
                    );
                }
                return response;
            },
            "base_import.import/execute_import": (route, args) => {
                assert.step("execute_import");
                assert.strictEqual(
                    args[3].date_format,
                    "%Y%m%d",
                    "date is converted to strftime as expected during the import"
                );
                return executeImport(args);
            },
        });

        // Set and trigger the change of a file for the input
        const file = new File(["fake_file"], "fake_file.csv", { type: "text/plain" });
        await editInput(target, ".o_control_panel_main_buttons input[type='file']", file);
        await editInput(target, ".o_import_date_format#date_format-3", "YYYYMMDD");

        // Parse the file again with the updated date format to check that
        // the format is correctly formatted in the UI
        await click(target.querySelector(".o_import_formatting button"));
        await click(
            $(target).find(
                ".o_control_panel_main_buttons > div:visible > button:contains(Import)"
            )[0]
        );
        assert.verifySteps(["execute_import"]);
        assert.strictEqual(
            target.querySelector(".o_import_date_format").value,
            "YYYYMMDD",
            "UI displays the human formatted date"
        );
    });

    QUnit.test("Import action: field selection has a clear button", async function (assert) {
        registerFakeHTTPService();
        patchWithCleanup(browser, {
            setTimeout: (fn) => fn(),
        });

        await createImportAction();

        // Set and trigger the change of a file for the input
        const file = new File(["fake_file"], "fake_file.xlsx", { type: "text/plain" });
        await editInput(target, ".o_control_panel_main_buttons input[type='file']", file);
        await editSelectMenu(target, ".o_import_data_content .o_select_menu", "Bar");
        assert.containsN(
            target,
            ".o_select_menu_toggler_clear",
            2,
            "clear button is present for each field to unselect it"
        );

        await click(target.querySelector(".o_select_menu_toggler_clear"));
        assert.strictEqual(
            target.querySelector("tr:nth-child(2) .o_select_menu").textContent,
            "To import, select a field...",
            "field has been unselected"
        );
    });

    QUnit.test(
        "Import a CSV: formatting options for date and datetime options",
        async function (assert) {
            registerFakeHTTPService((route, params) => {
                assert.strictEqual(route, "/base_import/set_file");
                assert.strictEqual(
                    params.ufile[0].name,
                    "fake_file.csv",
                    "file is correctly uploaded to the server"
                );
            });
            await createImportAction();

            // Set and trigger the change of a file for the input
            const file = new File(["fake_file"], "fake_file.csv", { type: "text/plain" });
            await editInput(target, ".o_control_panel_main_buttons input[type='file']", file);
            assert.strictEqual(
                target.querySelector(".o_import_date_format").list.id,
                "list-3",
                "a datalist is associated to the date input"
            );
            assert.containsOnce(
                target.querySelector(".o_import_date_format").previousElementSibling,
                "sup",
                "a tooltip is displayed on the label of the option"
            );
            assert.strictEqual(
                target.querySelector(".o_import_date_format").list.options[0].value,
                "YYYY-MM-DD",
                "an option for datetime has the right value"
            );
            assert.strictEqual(
                target.querySelector(".o_import_datetime_format").list.id,
                "list-4",
                "a datalist is associated to the datetime input"
            );
            assert.containsOnce(
                target.querySelector(".o_import_datetime_format").previousElementSibling,
                "sup",
                "a tooltip is displayed on the label of the option"
            );
            assert.strictEqual(
                target.querySelector(".o_import_datetime_format").list.options[0].value,
                "YYYY-MM-DD HH:mm:SS",
                "an option for datetime has the right value"
            );
            assert.containsOnce(
                target,
                ".o_import_action .o_import_data_content",
                "content panel is visible"
            );
        }
    );
});
