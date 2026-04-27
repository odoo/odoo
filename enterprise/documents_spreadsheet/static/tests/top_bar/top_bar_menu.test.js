import {
    DocumentsDocument,
    defineDocumentSpreadsheetModels,
    getBasicServerData,
} from "@documents_spreadsheet/../tests/helpers/data";
import {
    createSpreadsheet,
    mockActionService,
} from "@documents_spreadsheet/../tests/helpers/spreadsheet_test_utils";
import { describe, expect, test } from "@odoo/hoot";
import { press } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import * as spreadsheet from "@odoo/o-spreadsheet";
import { setCellContent } from "@spreadsheet/../tests/helpers/commands";
import { getCellContent, getCellValue } from "@spreadsheet/../tests/helpers/getters";
import { doMenuAction } from "@spreadsheet/../tests/helpers/ui";
import { UNTITLED_SPREADSHEET_NAME } from "@spreadsheet/helpers/constants";
import { contains, onRpc, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { download } from "@web/core/network/download";

defineDocumentSpreadsheetModels();
describe.current.tags("desktop");

const { topbarMenuRegistry } = spreadsheet.registries;

test("Can create a new spreadsheet from File menu", async function () {
    const spreadsheet = DocumentsDocument._records[1];
    const { env } = await createSpreadsheet({
        spreadsheetId: spreadsheet.id,
        mockRPC: async function (route, args) {
            if (
                args.method === "action_open_new_spreadsheet" &&
                args.model === "documents.document"
            ) {
                expect.step("action_open_new_spreadsheet");
            }
        },
    });
    await doMenuAction(topbarMenuRegistry, ["file", "new_sheet"], env);
    expect.verifySteps(["action_open_new_spreadsheet"]);
});

test("Display notification for new spreadsheet creation based on action response", async function () {
    const spreadsheet = DocumentsDocument._records[1];
    const action = {
        type: "ir.actions.client",
        tag: "display_notification",
        params: {
            type: "info",
            message: "New spreadsheet created in Documents",
            next: {
                type: "ir.actions.client",
                tag: "action_open_spreadsheet",
                params: {
                    spreadsheet_id: spreadsheet.id,
                    is_new_spreadsheet: true,
                },
            },
        },
    };

    const { env } = await createSpreadsheet({
        spreadsheetId: spreadsheet.id,
        mockRPC: async function (route, args) {
            if (
                args.method === "action_open_new_spreadsheet" &&
                args.model === "documents.document"
            ) {
                expect.step("action_open_new_spreadsheet");
                return action;
            }
        },
    });

    const file = topbarMenuRegistry.getAll().find((item) => item.id === "file");
    const newSheet = file.children.find((item) => item.id === "new_sheet");
    await newSheet.execute(env);
    expect.verifySteps(["action_open_new_spreadsheet"]);

    await animationFrame(); // Wait for the notification to be displayed
    expect(".o_notification_content").toHaveText("New spreadsheet created in Documents");
});

test("Action action_download_spreadsheet is correctly fired with topbar menu", async function () {
    onRpc("/spreadsheet/xlsx", () => {});
    let actionParam;
    const { env, model } = await createSpreadsheet();
    mockActionService((action) => (actionParam = action.params));
    const file = topbarMenuRegistry.getAll().find((item) => item.id === "file");
    const download = file.children.find((item) => item.id === "download");
    await download.execute(env);
    expect(actionParam).toEqual({
        xlsxData: model.exportXLSX(),
        name: UNTITLED_SPREADSHEET_NAME.toString(),
        sources: [],
    });
});

test("Datasources are loaded before exporting in Excel", async function () {
    const spreadsheetData = {
        version: 16,
        sheets: [
            {
                id: "sh1",
            },
            {
                id: "sh2",
                cells: {
                    A2: { content: `=ODOO.PIVOT(1,"probability","bar","false","foo",2)` },
                },
            },
        ],
        pivots: {
            1: {
                id: 1,
                colGroupBys: ["foo"],
                domain: [],
                measures: [{ field: "probability", operator: "avg" }],
                model: "partner",
                rowGroupBys: ["bar"],
                context: {},
            },
        },
    };
    const serverData = getBasicServerData();
    serverData.models["documents.document"].records = [
        DocumentsDocument._records[0], // keep the res_company.document_spreadsheet_folder_id
        {
            id: 45,
            spreadsheet_data: JSON.stringify(spreadsheetData),
            name: "Spreadsheet",
            handler: "spreadsheet",
        },
    ];
    const { model, env } = await createSpreadsheet({
        serverData,
        spreadsheetId: 45,
    });
    mockActionService((action) => expect.step(getCellValue(model, "A2", "sh2").toString()));
    const file = topbarMenuRegistry.getAll().find((item) => item.id === "file");
    const download = file.children.find((item) => item.id === "download");
    await download.execute(env);
    expect.verifySteps(["15"]);
});

test("Can download xlsx file", async function () {
    patchWithCleanup(download, {
        _download: async (options) => {
            expect.step(options.url);
            expect(options.data.zip_name).not.toBe(undefined);
            expect(options.data.files).not.toBe(undefined);
        },
    });
    const { env } = await createSpreadsheet();
    const file = topbarMenuRegistry.getAll().find((item) => item.id === "file");
    const downloadMenuItem = file.children.find((item) => item.id === "download");
    await downloadMenuItem.execute(env);
    expect.verifySteps(["/spreadsheet/xlsx"]);
});

test("Can make a copy", async function () {
    const spreadsheet = DocumentsDocument._records[1];
    const { env, model } = await createSpreadsheet({
        spreadsheetId: spreadsheet.id,
        mockRPC: async function (route, args) {
            if (args.method === "copy" && args.model === "documents.document") {
                expect.step("copy");
                expect(args.kwargs.default.spreadsheet_snapshot).toBe(false, {
                    message: "It should reset the snapshot",
                });
                expect(args.kwargs.default.spreadsheet_revision_ids).toEqual([], {
                    message: "It should reset the revisions",
                });
                expect(args.kwargs.default.spreadsheet_data).toBe(
                    JSON.stringify(model.exportData()),
                    { message: "It should copy the data" }
                );
                return [1];
            }
        },
    });
    const file = topbarMenuRegistry.getAll().find((item) => item.id === "file");
    const makeCopy = file.children.find((item) => item.id === "make_copy");
    await makeCopy.execute(env);
    expect.verifySteps(["copy"]);
});

test("Lazy load currencies", async function () {
    const { env } = await createSpreadsheet({
        mockRPC: async function (route, args) {
            if (args.method === "search_read" && args.model === "res.currency") {
                expect.step("currencies-loaded");
                return [
                    {
                        decimalPlaces: 2,
                        name: "Euro",
                        code: "EUR",
                        symbol: "€",
                        position: "after",
                    },
                ];
            }
        },
    });
    expect.verifySteps([]);
    const menuPath = ["format", "format_number", "format_custom_currency"];
    await doMenuAction(topbarMenuRegistry, menuPath, env);
    await animationFrame();
    await contains(".o-sidePanelClose").click();
    await doMenuAction(topbarMenuRegistry, menuPath, env);
    await animationFrame();
    expect.verifySteps(["currencies-loaded"]);
});

test("Can Insert odoo formulas from Insert > Functions > Odoo", async function () {
    const { model } = await createSpreadsheet();

    setCellContent(model, "A1", `Hi :)`);

    // Skip the visibility checks because on small screens (height <~700 px) the menus become too
    // tall for the screen and need to be scrolled to have the "Odoo" menu item visible.
    const skipVisibilityChecks = { visible: false, display: false };
    await contains(".o-topbar-menu[data-id='insert']", skipVisibilityChecks).click();
    await contains(".o-menu-item[data-name='insert_function']", skipVisibilityChecks).click();
    await contains(".o-menu-item[title='Odoo']", skipVisibilityChecks).click();
    await contains(".o-menu-item[title='ODOO.CURRENCY.RATE']", skipVisibilityChecks).click();

    await press("Enter");
    await animationFrame();

    expect(getCellContent(model, "A1")).toBe("=ODOO.CURRENCY.RATE()");
});
