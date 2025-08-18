import { before, describe, expect, test } from "@odoo/hoot";
import { animationFrame, drag, queryOne, setInputFiles } from "@odoo/hoot-dom";
import { useEffect } from "@odoo/owl";
import {
    contains,
    defineActions,
    defineModels,
    fields,
    getService,
    mockService,
    models,
    mountWebClient,
    onRpc,
    patchWithCleanup,
    serverState,
} from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";
import { redirect } from "@web/core/utils/urls";
import { ImportAction } from "../src/import_action/import_action";
import { ImportBlockUI } from "../src/import_block_ui";
import { ImportDataProgress } from "../src/import_data_progress/import_data_progress";

const FAKE_PREVIEW_HEADERS = ["Foo", "Bar", "Display name"];
const FAKE_PREVIEW_DATA = [
    ["Deco addict", "Azure Interior", "Brandon Freeman"],
    ["1", "1", "0"],
    ["Azure Interior"],
];

class Partner extends models.Model {
    name = fields.Char();
    foo = fields.Char();
    bar = fields.Boolean({ model_name: "partner" });
    selection = fields.Selection({
        selection: [
            ["item_1", "First Item"],
            ["item_2", "Second item"],
        ],
        model_name: "partner",
    });
    many2many_field = fields.Many2many({
        relation: "partner",
        comodel_name: "comodel.test",
    });
    _records = [];
}

defineModels([Partner]);

defineActions([
    {
        id: 1,
        name: "Import Data",
        path: "import",
        tag: "import",
        target: "current",
        type: "ir.actions.client",
        params: {
            active_model: "partner",
        },
    },
]);

let totalRows = 0;

async function executeImport(data, shouldWait = false) {
    const res = { ids: [] };
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
    if (data[3].skip + 1 < totalRows) {
        res.nextrow = data[3].skip + data[3].limit;
    } else {
        res.nextrow = 0;
    }

    if (shouldWait) {
        // make sure the progress bar is shown
        await animationFrame();
    }

    return res;
}

function getFieldsTree() {
    const mappedFields = Object.entries(Partner._fields).map(([k, v]) => ({
        ...v,
        id: k,
        fields: [],
    }));
    return mappedFields.filter((e) => !["id", "__last_update", "name"].includes(e.id));
}

function getMatches(headers) {
    // basic implementation for testing purposes which matches if the first line is the
    // name of a field, or corresponds to the string value of a field from Partner
    const matches = [];
    for (const header of headers) {
        if (Partner._fields[header]) {
            matches.push([header]);
        }
        const fieldIndex = Object.values(Partner._fields).findIndex((e) => e.string === header);
        if (fieldIndex !== -1) {
            matches.push([Object.keys(Partner._fields)[fieldIndex]]);
        }
    }
    return Object.assign({}, matches);
}

async function parsePreview(opts, overrides = {}) {
    const fields = overrides.fields ?? getFieldsTree();
    const headers = overrides.headers ?? FAKE_PREVIEW_HEADERS;
    const data = overrides.data ?? FAKE_PREVIEW_DATA;
    const matches = overrides.matches ?? (opts.has_headers ? getMatches(headers) : null);
    const preview =
        overrides.preview ?? (opts.has_headers ? data : data.map((c, i) => [headers[i], ...c]));
    totalRows = overrides.rowCount ?? [...preview].sort((a, b) => b.length - a.length)[0].length;

    const errorValues = ["#NULL!", "#DIV/0!", "#VALUE!", "#REF!", "#NAME?", "#NUM!", "#N/A"];
    const error = preview.flat().find((cell) => errorValues.includes(cell));
    if (error) {
        return {
            preview: undefined,
            error: `Invalid cell value: ${error}`,
        };
    }

    return {
        advanced_mode: opts.advanced,
        batch: false,
        fields,
        num_rows: totalRows,
        header_types: false,
        headers: opts.has_headers ? headers : false,
        matches,
        options: {
            ...opts,
            sheet: opts.sheet.length ? opts.sheet : "Template",
            sheets: ["Template", "Template 2"],
        },
        preview,
    };
}

// since executing a real import would be difficult, this method simply returns
// some error messages to help testing the UI
function executeFailingImport(field, isMultiline, field_path = "") {
    let moreInfo = [];
    if (Partner._fields[field].type === "selection") {
        moreInfo = Partner._fields[field].selection;
    }
    return {
        ids: false,
        messages: isMultiline
            ? [
                  {
                      field,
                      field_name: Partner._fields[field].string,
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
                      field_name: Partner._fields[field].string,
                      field_path,
                      message: "Duplicate value",
                      moreInfo,
                      record: 0,
                      rows: { from: 1, to: 1 },
                      priority: "error",
                  },
                  {
                      field,
                      field_name: Partner._fields[field].string,
                      field_path,
                      message: "Wrong values",
                      moreInfo,
                      record: 0,
                      rows: { from: 2, to: 3 },
                      priority: "warning",
                  },
                  {
                      field,
                      field_name: Partner._fields[field].string,
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
                      field_name: Partner._fields[field].string,
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
                      field_name: Partner._fields[field].string,
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

onRpc("partner", "get_import_templates", () => []);
onRpc("base_import.import", "parse_preview", ({ args }) => parsePreview(args[1]));
onRpc("base_import.import", "execute_import", ({ args }) => executeImport(args));
onRpc("base_import.import", "create", () => 11);
onRpc("base_import.import", "get_fields", () => Partner._fields);

before(() => {
    mockService("http", {
        async post(route, params) {
            return JSON.stringify([
                {
                    id: 10,
                    name: params.ufile[0].name,
                    mimetype: "text/plain",
                },
            ]);
        },
    });
});

describe("Import view", () => {
    test.tags("desktop");
    test("UI before file upload", async () => {
        const templateURL = "/myTemplateURL.xlsx";

        redirect("/odoo");

        onRpc("partner", "get_import_templates", ({ route }) => {
            expect.step(route);
            return [{ label: "Some Import Template", template: templateURL }];
        });
        onRpc("base_import.import", "create", ({ route }) => expect.step(route));
        await mountWebClient();
        await getService("action").doAction(1);
        await animationFrame(); // pushState is debounced
        expect.verifySteps([
            "/web/dataset/call_kw/partner/get_import_templates",
            "/web/dataset/call_kw/base_import.import/create",
        ]);
        expect(browser.location.href).toBe(
            "https://www.hoot.test/odoo/import?active_model=partner",
            {
                message: "the url contains the active_model",
            }
        );
        expect(".o_import_action").toHaveCount(1);
        expect(".o_nocontent_help .btn-outline-primary").toHaveText("Some Import Template");
        expect(".o_nocontent_help .btn-outline-primary").toHaveProperty(
            "href",
            "https://www.hoot.test" + templateURL
        );
        expect(".o_control_panel button").toHaveCount(2);
    });

    test("import a file with multiple sheets", async () => {
        mockService("http", {
            post(route, params) {
                expect.step(route);
                expect(params.ufile[0].name).toBe("fake_file.xlsx");
                return super.post(route, params);
            },
        });

        onRpc("partner", "get_import_templates", ({ route }) => expect.step(route));
        onRpc("base_import.import", "parse_preview", ({ route }) => expect.step(route));
        onRpc("base_import.import", "create", ({ route }) => expect.step(route));

        await mountWebClient();
        await getService("action").doAction(1);
        expect.verifySteps([
            "/web/dataset/call_kw/partner/get_import_templates",
            "/web/dataset/call_kw/base_import.import/create",
        ]);
        // Set and trigger the change of a file for the input
        const file = new File(["fake_file"], "fake_file.xlsx", { type: "text/plain" });
        await contains(".o_control_panel_main_buttons .o_import_file").click();
        await setInputFiles([file]);
        await animationFrame();
        expect.verifySteps([
            "/base_import/set_file",
            "/web/dataset/call_kw/base_import.import/parse_preview",
        ]);
        expect(".o_import_action .o_import_data_sidepanel").toHaveCount(1);
        expect(".o_import_action .o_import_data_content").toHaveCount(1);
        expect(".o_import_data_sidepanel .fst-italic.truncate").toHaveText("fake_file", {
            message: "filename is shown and can be truncated",
        });
        expect(".o_import_data_sidepanel .fst-italic:not(.truncate)").toHaveText(".xlsx", {
            message: "file extension is displayed on its own",
        });
        expect(".o_import_data_sidepanel [name=o_import_sheet]").toHaveValue("Template");

        expect(".o_import_data_content tbody > tr").toHaveCount(3, {
            message: "recognized values are displayed in the view",
        });
        expect(
            ".o_import_data_content tr:eq(1) .o_import_file_column_cell > span:eq(0)"
        ).toHaveText("Foo");
        expect(
            ".o_import_data_content tr:eq(1) .o_import_file_column_cell > span:eq(1)"
        ).toHaveText("Deco addict");
        expect(
            ".o_import_data_content tr:eq(1) .o_import_file_column_cell > span:eq(1)"
        ).toHaveAttribute(
            "data-tooltip-info",
            '{"lines":["Deco addict","Azure Interior","Brandon Freeman"]}'
        );
        expect(".o_import_data_content tbody td:nth-child(3) .alert-info").toHaveCount(0);

        // Select a field already selected for another column
        await contains(".o_import_data_content .o_select_menu").selectDropdownItem("Display name");
        expect(".o_import_data_content tbody td:nth-child(3) .alert-info").toHaveCount(2);
        expect(".o_import_data_content tbody td:nth-child(3) .alert-info").toHaveText(
            "This column will be concatenated in field Display name"
        );

        // Preview the second sheet
        await contains(".o_import_data_sidepanel [name=o_import_sheet]").select("Template 2");
        expect.verifySteps(["/web/dataset/call_kw/base_import.import/parse_preview"]);
        expect(".o_import_data_sidepanel [name=o_import_sheet]").toHaveValue("Template 2");
        expect(".o_import_data_content tbody td:nth-child(3) .alert-info").toHaveCount(0);
    });

    test("preview error on loading second sheet", async () => {
        mockService("http", {
            post(route, params) {
                expect.step(route);
                expect(params.ufile[0].name).toBe("fake_file.xlsx");
                return super.post(route, params);
            },
        });

        let currentSheet = "Template"; // Track the current sheet being parsed-
        onRpc("partner", "get_import_templates", ({ route }) => expect.step(route));
        onRpc("base_import.import", "parse_preview", ({ route, args }) => {
            expect.step(route);

            // Determine preview data based on the selected sheet
            const fakePreviewData = [...FAKE_PREVIEW_DATA];
            if (currentSheet !== "Template") {
                fakePreviewData[2] = ["Display name", "#N/A"];
            }

            return parsePreview(args[1], {
                data: fakePreviewData,
            });
        });
        onRpc("base_import.import", "create", ({ route }) => expect.step(route));
        await mountWebClient();
        await getService("action").doAction(1);
        expect.verifySteps([
            "/web/dataset/call_kw/partner/get_import_templates",
            "/web/dataset/call_kw/base_import.import/create",
        ]);

        // Simulate uploading a file
        const file = new File(["fake_file"], "fake_file.xlsx", { type: "text/plain" });
        await contains(".o_control_panel_main_buttons .o_import_file").click();
        await setInputFiles([file]);
        await animationFrame();
        expect.verifySteps([
            "/base_import/set_file",
            "/web/dataset/call_kw/base_import.import/parse_preview",
        ]);

        // Check the initial state after parsing the first sheet
        expect(".o_import_action .o_import_data_sidepanel").toHaveCount(1);
        expect(".o_import_action .o_import_data_content").toHaveCount(1);

        // Change to the second sheet
        currentSheet = "Template 2"; // Update the current sheet
        await contains(".o_import_data_sidepanel [name=o_import_sheet]").select(currentSheet);
        expect.verifySteps(["/web/dataset/call_kw/base_import.import/parse_preview"]);

        // Verify the error for second sheet preview
        expect(".o_import_data_content p:first").toHaveText(
            'Import preview failed due to: " Invalid cell value: #N/A ".'
        );
    });

    test("default import options are correctly", async () => {
        onRpc("base_import.import", "execute_import", ({ args }) => {
            expect.step("execute_import");
            expect(args[3]).toEqual({
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
            });
        });

        await mountWebClient();
        await getService("action").doAction(1);

        // Set and trigger the change of a file for the input
        const file = new File(["fake_file"], "fake_file.xls", { type: "text/plain" });
        await contains(".o_control_panel_main_buttons .o_import_file").click();
        await setInputFiles([file]);
        await animationFrame();
        await contains(".o_control_panel_main_buttons button:first-child").click();
        expect.verifySteps(["execute_import"]);
    });

    test(`import a CSV file with one sheet`, async () => {
        mockService("http", {
            post(route, params) {
                expect.step(route);
                expect(params.ufile[0].name).toBe("fake_file.csv");
                return super.post(route, params);
            },
        });

        await mountWebClient();
        await getService("action").doAction(1);
        await animationFrame();

        // Set and trigger the change of a file for the input
        const file = new File(["fake_file"], "fake_file.csv", { type: "text/plain" });
        await contains(".o_control_panel_main_buttons .o_import_file").click();
        await setInputFiles([file]);
        await animationFrame();
        expect.verifySteps(["/base_import/set_file"]);
        expect(`.o_import_data_sidepanel .o_import_formatting`).toHaveCount(1);
        expect(`.o_import_action .o_import_data_content`).toHaveCount(1);
    });

    test.tags("desktop");
    test("drag-and-drop file support", async () => {
        onRpc("has_group", () => true);
        mockService("http", {
            post(route, params) {
                expect.step(route);
                expect(params.ufile[0].name).toBe("fake_file.csv");
                return super.post(route, params);
            },
        });
        mockService("notification", {
            add: (message) => {
                expect.step(message);
                return () => {};
            },
        });
        mockService("action", {
            doAction(action) {
                expect.step("action");
                if (action !== 1) {
                    expect(action).toEqual({
                        type: "ir.actions.act_window",
                        name: "Imported records",
                        res_model: "partner",
                        view_mode: "tree,form",
                        views: [
                            [false, "list"],
                            [false, "form"],
                        ],
                        domain: [["id", "in", [1]]],
                        target: "current",
                    });
                }
                return super.doAction(...arguments);
            },
        });
        onRpc("base_import.import", "execute_import", ({ route }) => {
            expect.step(route);
        });
        await mountWebClient();
        await getService("action").doAction(1);
        expect.verifySteps(["action"]);
        queryOne(".o_nocontent_help").draggable = true;
        const file = new File(["fake_file"], "fake_file.csv", {
            type: "text/plain",
        });
        const { moveTo, drop } = await drag(".o_nocontent_help", { files: [file] });
        await moveTo(".o_import_action");
        await animationFrame();
        await drop(".o-Dropzone");
        await animationFrame();
        expect(".o_import_action .o_import_data_content").toHaveCount(1);
        expect.verifySteps(["/base_import/set_file"]);
        await contains(".o_control_panel_main_buttons button:first").click();
        expect.verifySteps(["/web/dataset/call_kw/base_import.import/execute_import"]);
        await contains(".o_control_panel_main_buttons button:first").click();
        expect.verifySteps([
            "/web/dataset/call_kw/base_import.import/execute_import",
            "1 records successfully imported",
            "action",
        ]);
        expect(".o_list_view").toHaveCount(1);
    });

    test("cancel in import view", async () => {
        await mountWebClient();
        await getService("action").doAction({
            name: "Fall back",
            type: "ir.actions.client",
            tag: "import",
            params: { active_model: "partner" },
        });
        expect(".o_last_breadcrumb_item span").toHaveText("Fall back");
        await getService("action").doAction(1);
        expect(".o_last_breadcrumb_item span").toHaveText("Import Data");
        await contains(".o_control_panel_main_buttons button:contains(Cancel)").click();
        expect(".o_last_breadcrumb_item span").toHaveText("Fall back");
    })

    test("additional options in debug", async () => {
        serverState.debug = "1";

        await mountWebClient();
        onRpc("base_import.import", "parse_preview", ({ route, args }) => {
            expect.step(route);
            expect(args[1].advanced).toBe(true);
        });
        await getService("action").doAction(1);

        // Set and trigger the change of a file for the input
        const file = new File(["fake_file"], "fake_file.csv", { type: "text/plain" });
        await contains(".o_control_panel_main_buttons .o_import_file").click();
        await setInputFiles([file]);
        await animationFrame();
        expect.verifySteps(["/web/dataset/call_kw/base_import.import/parse_preview"]);

        expect(".o_import_data_sidepanel .o_import_debug_options").toHaveCount(1, {
            message: "additional options are present in the side panel in debug mode",
        });
    });

    test("execute import with option 'use first row as headers'", async () => {
        mockService("notification", {
            add: (message) => {
                expect.step(message);
                return () => {};
            },
        });

        await mountWebClient();
        onRpc("base_import.import", "parse_preview", ({ route }) => {
            expect.step(route);
        });
        onRpc("base_import.import", "execute_import", ({ route }) => {
            expect.step(route);
        });
        await getService("action").doAction(1);

        // Set and trigger the change of a file for the input
        const file = new File(["fake_file"], "fake_file.xls", { type: "text/plain" });
        await contains(".o_control_panel_main_buttons .o_import_file").click();
        await setInputFiles([file]);
        await animationFrame();
        await animationFrame();
        expect(".o_import_data_sidepanel input[type=checkbox]").toBeChecked();
        expect.verifySteps(["/web/dataset/call_kw/base_import.import/parse_preview"]);
        expect(
            ".o_import_data_content tr:eq(1) .o_import_file_column_cell > span:eq(0)"
        ).toHaveText("Foo", {
            message: "first row is used as column title",
        });
        expect(".o_import_data_content .o_select_menu:first").toHaveText("Foo", {
            message:
                "as the column header could match with a database field, it is selected by default",
        });

        await contains(".o_import_data_sidepanel input[type=checkbox]").click();
        expect.verifySteps(["/web/dataset/call_kw/base_import.import/parse_preview"]);
        expect(
            ".o_import_data_content tr:eq(1) .o_import_file_column_cell > span:eq(0)"
        ).toHaveText("Foo, Deco addict, Azure Interior, Brandon Freeman");
        expect(".o_import_data_content .o_select_menu").toHaveText("To import, select a field...", {
            message: "as the column couldn't match with the database, user must make a choice",
        });

        await contains(".o_control_panel_main_buttons button:first-child").click();
        expect(".o_notification_body").toHaveCount(0, {
            message: "should not display a notification",
        });
        expect.verifySteps(["/web/dataset/call_kw/base_import.import/execute_import"]);
        expect(".o_import_data_content .alert-info").toHaveCount(1);
        expect(".o_import_data_content .alert-danger").toHaveCount(1);
        expect(".o_import_data_content .alert-danger").toHaveText(
            "You must configure at least one field to import"
        );

        await contains(".o_import_data_content .o_select_menu").selectDropdownItem("Display name");
        await contains(".o_control_panel_main_buttons button:nth-child(2)").click();
        expect.verifySteps([
            "/web/dataset/call_kw/base_import.import/execute_import",
            "1 records successfully imported",
        ]);
    });

    test("import data that don't match (selection)", async () => {
        Partner._fields.selection.required = true;
        let shouldFail = true;

        await mountWebClient();
        onRpc("base_import.import", "execute_import", ({ args }) => {
            if (shouldFail) {
                shouldFail = false;
                return executeFailingImport(args[1][0]);
            }
            expect(args[3].fallback_values).toEqual(
                {
                    selection: {
                        fallback_value: "item_2",
                        field_model: "partner",
                        field_type: "selection",
                    },
                },
                { message: "selected fallback value has been given to the request" }
            );
        });
        await getService("action").doAction(1);

        // Set and trigger the change of a file for the input
        const file = new File(["fake_file"], "fake_file.xlsx", { type: "text/plain" });
        await contains(".o_control_panel_main_buttons .o_import_file").click();
        await setInputFiles([file]);
        await animationFrame();
        // For this test, we force the display of an error message if this field is set
        await contains(".o_import_data_content .o_select_menu").selectDropdownItem("Selection");
        await contains(".o_control_panel_main_buttons button:nth-child(2)").click();
        expect(".o_import_data_content .alert-danger:first").toHaveText(
            "The file contains blocking errors (see below)",
            { message: "a message is shown if the import was blocked" }
        );
        expect(".o_import_report p").toHaveText("Incorrect value", {
            message: "the message is displayed in the view",
        });
        expect(".o_import_field_selection").toHaveCount(1, {
            message: "an action can be set when the column cannot match a field",
        });
        expect(".o_import_field_selection select").toHaveText(
            "Prevent import\nSet to: First Item\nSet to: Second item",
            { message: "'skip' option is not available, since the field is required" }
        );
        expect(".o_import_field_selection select option:selected").toHaveText("Prevent import", {
            message: "prevent option is selected by default",
        });
        contains(".o_import_field_selection select").select("item_2");
        await contains(".o_control_panel_main_buttons button:first-child").click();
        expect(".o_import_data_content .alert-info").toHaveText("Everything seems valid.", {
            message: "import is now successful",
        });
        expect(".o_import_field_selection").toHaveCount(1, {
            message:
                "options are still present to change the action to do when the column don't match",
        });
    });

    test("import data that don't match (boolean)", async () => {
        let shouldFail = true;

        await mountWebClient();
        onRpc("base_import.import", "execute_import", ({ args }) => {
            if (shouldFail) {
                shouldFail = false;
                return executeFailingImport(args[1][0]);
            }
            expect(args[3].fallback_values).toEqual(
                {
                    bar: {
                        fallback_value: "false",
                        field_model: "partner",
                        field_type: "boolean",
                    },
                },
                { message: "selected fallback value has been given to the request" }
            );
        });
        await getService("action").doAction(1);

        // Set and trigger the change of a file for the input
        const file = new File(["fake_file"], "fake_file.xlsx", { type: "text/plain" });
        await contains(".o_control_panel_main_buttons .o_import_file").click();
        await setInputFiles([file]);
        await animationFrame();
        // For this test, we force the display of an error message if this field is set
        await contains(".o_import_data_content .o_select_menu").selectDropdownItem("Bar");
        await contains(".o_control_panel_main_buttons button:nth-child(2)").click();
        expect(".o_import_data_content .alert-danger:first").toHaveText(
            "The file contains blocking errors (see below)",
            { message: "a message is shown if the import was blocked" }
        );
        expect(".o_import_field_boolean select").toHaveText(
            "Prevent import\nSet to: False\nSet to: True\nSkip record"
        );
        contains(".o_import_field_boolean select").select("false");
        await contains(".o_control_panel_main_buttons button:first-child").click();
        expect(".o_import_data_content .alert-info").toHaveText("Everything seems valid.");
    });

    test("import data that don't match (many2many)", async () => {
        let executeCount = 0;

        await mountWebClient();
        onRpc("base_import.import", "execute_import", ({ args }) => {
            expect.step("execute_import");
            executeCount++;
            if (executeCount === 1) {
                return executeFailingImport(args[1][0]);
            }
            if (executeCount === 2) {
                expect(args[3].name_create_enabled_fields).toEqual(
                    {
                        many2many_field: true,
                    },
                    { message: "selected fallback value has been given to the request" }
                );
            } else {
                expect(args[3].name_create_enabled_fields).toEqual(
                    {},
                    { message: "selected fallback value has been given to the request" }
                );
                expect(args[3].import_skip_records).toEqual(["many2many_field"], {
                    message: "selected fallback value has been given to the request",
                });
            }
        });
        await getService("action").doAction(1);

        // Set and trigger the change of a file for the input
        const file = new File(["fake_file"], "fake_file.xlsx", { type: "text/plain" });
        await contains(".o_control_panel_main_buttons .o_import_file").click();
        await setInputFiles([file]);
        await animationFrame();
        // For this test, we force the display of an error message if this field is set
        await contains(".o_import_data_content .o_select_menu").selectDropdownItem("Many2Many");
        await contains(".o_control_panel_main_buttons button:first-child").click();
        expect.verifySteps(["execute_import"]);
        expect(".o_import_data_content .alert-danger:first").toHaveText(
            "The file contains blocking errors (see below)",
            { message: "a message is shown if the import was blocked" }
        );
        expect(".o_import_field_many2many select").toHaveText(
            "Prevent import\nSet value as empty\nSkip record\nCreate new values"
        );
        await contains(".o_import_field_many2many select").select("name_create_enabled_fields");
        await contains(".o_control_panel_main_buttons button:first-child").click();
        expect.verifySteps(["execute_import"]);
        expect(".o_import_data_content .alert-info:first").toHaveText("Everything seems valid.", {
            message: "import is now successful",
        });
        await contains(".o_import_field_many2many select").select("import_skip_records");
        await contains(".o_control_panel_main_buttons button:nth-child(2)").click();
        expect.verifySteps(["execute_import"]);
        expect(".o_import_data_content .alert-info:first").toHaveText("Everything seems valid.", {
            message: "import is still successful",
        });
    });

    test("import messages are grouped and sorted", async () => {
        mockService("http", () => ({
            post(route, params) {
                const file = {
                    id: 10,
                    name: params.ufile[0].name,
                    mimetype: "text/plain",
                };
                return JSON.stringify([file]);
            },
        }));

        await mountWebClient();
        onRpc("base_import.import", "execute_import", ({ args }) =>
            executeFailingImport(args[1][0], true)
        );
        onRpc("base_import.import", "get_fields", () => {
            expect.step("base_import.import/get_fields");
            return Partner._fields;
        });
        await getService("action").doAction(1);

        // Set and trigger the change of a file for the input
        const file = new File(["fake_file"], "fake_file.xlsx", { type: "text/plain" });
        await contains(".o_control_panel_main_buttons .o_import_file").click();
        await setInputFiles([file]);
        await animationFrame();
        await contains(".o_control_panel_main_buttons button:nth-child(1)").click();
        expect(".o_import_data_content .alert-danger:first").toHaveText(
            "The file contains blocking errors (see below)",
            { message: "a message is shown if the import was blocked" }
        );
        // Check that errors have been sorted and grouped
        expect(".o_import_report p").toHaveText("Multiple errors occurred in field Foo:");
        expect(".o_import_report li:first-child").toHaveText("Duplicate value at multiple rows");
        expect(".o_import_report li:nth-child(2)").toHaveText("Wrong values at multiple rows");
        expect(".o_import_report li:nth-child(3)").toHaveText("Bad value at row 5");
        expect(".o_import_report li").toHaveCount(3, {
            message: "only 3 errors are visible by default",
        });
        expect(".o_import_report_count").toHaveText("1 more");

        await contains(".o_import_report_count").click();
        expect(".o_import_report_count + li").toHaveText(
            "Invalid value at row 1 (Some invalid content)"
        );
    });

    test("test import in batches", async () => {
        let executeImportCount = 0;

        patchWithCleanup(ImportAction.prototype, {
            get isBatched() {
                // make sure the UI displays the batched import options
                return true;
            },
        });

        await mountWebClient();
        onRpc("base_import.import", "execute_import", ({ args }) => {
            expect(args[1]).toEqual(["foo", "bar", "display_name"], {
                message: "param contains the list of matching fields",
            });
            expect(args[2]).toEqual(["foo", "bar", "display name"], {
                message: "param contains the list of associated columns",
            });
            expect(args[3].limit).toBe(1, {
                message: "limit option is equal to the value set in the view",
            });
            expect(args[3].skip).toBe(executeImportCount * args[3].limit, {
                message: "skip option increments at each import",
            });
            executeImportCount++;
        });
        await getService("action").doAction(1);

        // Set and trigger the change of a file for the input
        const file = new File(["fake_file"], "fake_file.xls", { type: "text/plain" });
        await contains(".o_control_panel_main_buttons .o_import_file").click();
        await setInputFiles([file]);
        await animationFrame();
        expect("input#o_import_batch_limit").toHaveValue("2000");
        expect("input#o_import_row_start").toHaveValue("1");

        await contains("input#o_import_batch_limit").edit(1);
        await contains(".o_control_panel_main_buttons button:first").click();
        expect(".o_import_data_content .alert-info").toHaveText("Everything seems valid.", {
            message: "a message is shown if the import test was successfull",
        });
        expect(executeImportCount).toBe(3, { message: "execute_import was called 3 times" });
    });

    test("execute and pause import in batches", async () => {
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
                    expect.step("Block UI received the right text");
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
                            expect.step("pause triggered during step 2");
                            this.interrupt();
                        }
                    },
                    () => [this.props.importProgress.step]
                );

                expect(this.props.totalSteps).toBe(3, {
                    message: "progress bar receives the number of steps",
                });
                expect(this.props.importProgress).toEqual(
                    {
                        value: 0,
                        step: 1,
                    },
                    { message: "progress status has been given to the progress bar" }
                );
            },
        });

        await mountWebClient();
        onRpc("base_import.import", "execute_import", ({ args }) => executeImport(args, true));
        await getService("action").doAction(1);

        // Set and trigger the change of a file for the input
        const file = new File(["fake_file"], "fake_file.xls", { type: "text/plain" });
        await contains(".o_control_panel_main_buttons .o_import_file").click();
        await setInputFiles([file]);
        await animationFrame();
        await contains("input#o_import_batch_limit").edit(1);
        await contains(".o_control_panel_main_buttons button:nth-child(2)").click();
        // Since a animationFrame is added to each batch, we must wait twice before the end of the second batch
        await animationFrame();
        await animationFrame();
        expect.verifySteps(["Block UI received the right text", "pause triggered during step 2"]);
        expect(".o_import_data_content div .alert-warning").toHaveCount(1, {
            message: "a message is shown to indicate the user to resume from the third row",
        });
        expect(".o_import_data_content .alert-warning b:first-child").toHaveText(
            "Click 'Resume' to proceed with the import, resuming at line 2.",
            { message: "a message is shown to indicate the user to resume from the third row" }
        );
        expect(".o_control_panel_main_buttons button:nth-child(2)").toHaveText("Resume", {
            message: "button contains the right text",
        });
        expect("input#o_import_row_start").toHaveValue("2", {
            message: "the import will resume at line 2",
        });
        expect(".o_notification_body").toHaveText("1 records successfully imported", {
            message: "display a notification with the quantity of imported values",
        });
    });

    test("test and pause import in batches", async () => {
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
                    expect.step("Block UI received the right text");
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
                            expect.step("pause triggered during step 2");
                            this.interrupt();
                        }
                    },
                    () => [this.props.importProgress.step]
                );

                expect(this.props.totalSteps).toBe(3, {
                    message: "progress bar receives the number of steps",
                });
                expect(this.props.importProgress).toEqual(
                    {
                        value: 0,
                        step: 1,
                    },
                    { message: "progress status has been given to the progress bar" }
                );
            },
        });

        await mountWebClient();
        onRpc("base_import.import", "execute_import", ({ args }) => executeImport(args, true));
        await getService("action").doAction(1);

        // Set and trigger the change of a file for the input
        const file = new File(["fake_file"], "fake_file.xls", { type: "text/plain" });
        await contains(".o_control_panel_main_buttons .o_import_file").click();
        await setInputFiles([file]);
        await animationFrame();
        await contains("input#o_import_batch_limit").edit(1);
        await contains(".o_control_panel_main_buttons button:first").click();
        // Since an animationFrame is added to each batch, we must wait twice before the end of the second batch
        await animationFrame();
        await animationFrame();
        expect.verifySteps(["Block UI received the right text", "pause triggered during step 2"]);
        expect(".o_import_data_content .alert-info").toHaveText("Everything seems valid.");
        expect(".o_control_panel_main_buttons button:first").toHaveText("Import");
        expect("input#o_import_row_start").toHaveValue("1", {
            message: "the import will resume at line 1",
        });
    });

    test("relational fields correctly mapped on preview", async () => {
        await mountWebClient();
        onRpc("base_import.import", "parse_preview", ({ args }) =>
            parsePreview(args[1], {
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
            })
        );
        onRpc("base_import.import", "execute_import", ({ args }) => {
            expect.step("execute_import");
            expect(args[1]).toEqual(["id", "display_name", "many2many_field/id"]);
            expect(args[2]).toEqual(["id", "display_name", "many2many_field/id"]);
        });
        await getService("action").doAction(1);

        // Set and trigger the change of a file for the input
        const file = new File(["fake_file"], "fake_file.xls", { type: "text/plain" });
        await contains(".o_control_panel_main_buttons .o_import_file").click();
        await setInputFiles([file]);
        await animationFrame();

        expect("tr:nth-child(3) .o_import_file_column_cell span.text-truncate").toHaveText(
            "many2many_field/id",
            { message: "The third row should be the relational field" }
        );

        expect("tr:nth-child(3) .o_select_menu_toggler_slot span").toHaveText(
            "Many2Many / External ID",
            {
                message:
                    "The relational field should be selected by default and the name should be the full path.",
            }
        );

        await contains(".o_control_panel_main_buttons button:first-child").click();
        expect.verifySteps(["execute_import"]);
    });

    test("batch import relational fields", async () => {
        let executeImportCount = 0;

        patchWithCleanup(ImportAction.prototype, {
            get isBatched() {
                // Make sure the UI displays the batched import options
                return true;
            },
        });

        await mountWebClient();
        onRpc("base_import.import", "parse_preview", ({ args }) =>
            // Parse a file where all rows besides the first are used for relational data
            parsePreview(args[1], {
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
                preview: [["1"], ["Record Name"], ["1", "2", "3", "4", "5"]],
            })
        );
        onRpc("base_import.import", "execute_import", async ({ args }) => {
            ++executeImportCount;
            const res = await executeImport(args);
            // Import batch limit doesn't apply to relational fields, so set `nextrow`
            // to 0 to indicate all rows were imported on first call
            res.nextrow = 0;
            return res;
        });
        await getService("action").doAction(1);

        const file = new File(["fake_file"], "fake_file.xlsx", { type: "text/plain" });
        await contains(".o_control_panel_main_buttons .o_import_file").click();
        await setInputFiles([file]);
        await animationFrame();

        // Set batch limit to 1
        await contains("input#o_import_batch_limit").edit(1);

        await contains(".o_control_panel_main_buttons button:first-child").click();
        expect(".o_import_data_content .alert-info").toHaveText("Everything seems valid.", {
            message: "A message should indicate the import test was successful",
        });
        expect(executeImportCount).toBe(1, { message: "Execute import should finish in 1 step" });
    });

    test("import errors with relational fields", async () => {
        await mountWebClient();
        onRpc("base_import.import", "parse_preview", ({ args }) =>
            parsePreview(args[1], {
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
            })
        );
        onRpc("base_import.import", "execute_import", ({ args }) =>
            executeFailingImport(args[1][0], true, ["many2many_field", "id"])
        );
        await getService("action").doAction(1);

        // Set and trigger the change of a file for the input
        const file = new File(["fake_file"], "fake_file.xlsx", { type: "text/plain" });
        await contains(".o_control_panel_main_buttons .o_import_file").click();
        await setInputFiles([file]);
        await animationFrame();
        // For this test, we force the display of an error message if this field is set
        await contains(".o_import_data_content .o_select_menu").selectDropdownItem("Many2Many");
        await contains(".o_control_panel_main_buttons button:nth-child(2)").click();

        expect(".o_import_data_content .alert-danger:first").toHaveText(
            "The file contains blocking errors (see below)",
            { message: "A message is shown if the import was blocked" }
        );

        expect("tr:nth-child(3) .o_import_file_column_cell span.text-truncate").toHaveText(
            "many2many_field/id",
            { message: "The third row should be the relational field" }
        );

        expect("tr:nth-child(3) .o_select_menu_toggler_slot span").toHaveText(
            "Many2Many / External ID",
            { message: "The relational field is properly mapped" }
        );

        expect("tr:nth-child(3) .o_import_report.alert").toHaveCount(1, {
            message: "The relational field should have error messages on his row",
        });

        expect("tr:nth-child(3) .o_import_report.alert p b").toHaveText("Many2Many / External ID", {
            message: "The error should contain the full path of the relational field",
        });
    });

    test("date format should be converted to strftime", async () => {
        let parseCount = 0;
        await mountWebClient();
        onRpc("base_import.import", "parse_preview", async ({ args }) => {
            parseCount++;
            expect.step("parse_preview");
            const response = await parsePreview(args[1]);
            if (parseCount === 2) {
                expect(response.options.date_format).toBe("%Y%m%d", {
                    message: "server sends back a strftime formatted date",
                });
            }
            return response;
        });
        onRpc("base_import.import", "execute_import", ({ args }) => {
            expect.step("execute_import");
            expect(args[3].date_format).toBe("%Y%m%d", {
                message: "date is converted to strftime as expected during the import",
            });
        });
        await getService("action").doAction(1);

        // Set and trigger the change of a file for the input
        const file = new File(["fake_file"], "fake_file.csv", { type: "text/plain" });
        await contains(".o_control_panel_main_buttons .o_import_file").click();
        await setInputFiles([file]);
        await animationFrame();
        await contains(".o_import_date_format#date_format-3").edit("YYYYMMDD");

        // Parse the file again with the updated date format to check that
        // the format is correctly formatted in the UI
        await contains(".o_import_formatting button").click();
        await contains(
            ".o_control_panel_main_buttons > div:visible > button:contains(Import):eq(0)"
        ).click();
        expect.verifySteps(["parse_preview", "parse_preview", "execute_import"]);
        expect(".o_import_date_format").toHaveValue("YYYYMMDD", {
            message: "UI displays the human formatted date",
        });
    });
});

describe("Import action", () => {
    test("field selection has a clear button", async () => {
        await mountWebClient();
        await getService("action").doAction(1);

        // Set and trigger the change of a file for the input
        const file = new File(["fake_file"], "fake_file.xlsx", { type: "text/plain" });
        await contains(".o_control_panel_main_buttons .o_import_file").click();
        await setInputFiles([file]);
        await animationFrame();
        await contains(".o_import_data_content .o_select_menu").selectDropdownItem("Bar");
        expect(".o_select_menu_toggler_clear").toHaveCount(2, {
            message: "clear button is present for each field to unselect it",
        });

        await contains(".o_select_menu_toggler_clear").click();
        expect("tr:nth-child(2) .o_select_menu").toHaveText("To import, select a field...");
    });
});

describe("Import a CSV", () => {
    test("formatting options for date and datetime options", async () => {
        mockService("http", {
            post(route, params) {
                expect.step(route);
                expect(params.ufile[0].name).toBe("fake_file.csv");
                return super.post(route, params);
            },
        });
        await mountWebClient();
        await getService("action").doAction(1);

        // Set and trigger the change of a file for the input
        const file = new File(["fake_file"], "fake_file.csv", { type: "text/plain" });
        await contains(".o_control_panel_main_buttons .o_import_file").click();
        await setInputFiles([file]);
        await animationFrame();
        expect(".o_import_date_format").toHaveAttribute("list", "list-3", {
            message: "a datalist is associated to the date input",
        });
        expect("label:contains(Date Format) sup").toHaveCount(1, {
            message: "a tooltip is displayed on the label of the option",
        });
        expect("datalist#list-3 option:first").toHaveValue("YYYY-MM-DD");
        expect(".o_import_datetime_format").toHaveAttribute("list", "list-4", {
            message: "a datalist is associated to the datetime input",
        });
        expect("label:contains(Datetime Format) sup").toHaveCount(1, {
            message: "a tooltip is displayed on the label of the option",
        });
        expect("datalist#list-4 option:first").toHaveValue("YYYY-MM-DD HH:mm:SS");
        expect(".o_import_action .o_import_data_content").toHaveCount(1);
        expect.verifySteps(["/base_import/set_file"]);
    });
});
