/** @odoo-module */

import * as spreadsheet from "@odoo/o-spreadsheet";
import { getBasicServerData } from "@spreadsheet/../tests/utils/data";
import { doMenuAction } from "@spreadsheet/../tests/utils/ui";
import { click, mockDownload, nextTick, triggerEvent } from "@web/../tests/helpers/utils";
import { createSpreadsheet } from "../spreadsheet_test_utils";
import { mockActionService } from "@documents_spreadsheet/../tests/spreadsheet_test_utils";
import { UNTITLED_SPREADSHEET_NAME } from "@spreadsheet/helpers/constants";
import { setCellContent } from "@spreadsheet/../tests/utils/commands";
import { getCellContent, getCellValue } from "@spreadsheet/../tests/utils/getters";

const { topbarMenuRegistry } = spreadsheet.registries;

QUnit.module("documents_spreadsheet > Topbar Menu Items", {}, function () {
    QUnit.test("Can create a new spreadsheet from File menu", async function (assert) {
        const serverData = getBasicServerData();
        const spreadsheet = serverData.models["documents.document"].records[1];
        const { env } = await createSpreadsheet({
            spreadsheetId: spreadsheet.id,
            serverData,
            mockRPC: async function (route, args) {
                if (
                    args.method === "action_open_new_spreadsheet" &&
                    args.model === "documents.document"
                ) {
                    assert.step("action_open_new_spreadsheet");
                }
            },
        });
        await doMenuAction(topbarMenuRegistry, ["file", "new_sheet"], env);
        assert.verifySteps(["action_open_new_spreadsheet"]);
    });

    QUnit.test(
        "Action action_download_spreadsheet is correctly fired with topbar menu",
        async function (assert) {
            let actionParam;
            const { env, model } = await createSpreadsheet();
            mockActionService(env, (action) => (actionParam = action.params));
            const file = topbarMenuRegistry.getAll().find((item) => item.id === "file");
            const download = file.children.find((item) => item.id === "download");
            await download.execute(env);
            assert.deepEqual(actionParam, {
                xlsxData: model.exportXLSX(),
                name: UNTITLED_SPREADSHEET_NAME,
            });
        }
    );

    QUnit.test("Datasources are loaded before exporting in Excel", async function (assert) {
        const spreadsheetData = {
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
        serverData.models["documents.document"].records.push({
            id: 45,
            spreadsheet_data: JSON.stringify(spreadsheetData),
            name: "Spreadsheet",
            handler: "spreadsheet",
        });
        const { model, env } = await createSpreadsheet({
            serverData,
            spreadsheetId: 45,
        });
        mockActionService(env, (action) =>
            assert.step(getCellValue(model, "A2", "sh2").toString())
        );
        const file = topbarMenuRegistry.getAll().find((item) => item.id === "file");
        const download = file.children.find((item) => item.id === "download");
        await download.execute(env);
        assert.verifySteps(["15"]);
    });

    QUnit.test("Can download xlsx file", async function (assert) {
        mockDownload((options) => {
            assert.step(options.url);
            assert.ok(options.data.zip_name);
            assert.ok(options.data.files);
        });
        const { env } = await createSpreadsheet();
        const file = topbarMenuRegistry.getAll().find((item) => item.id === "file");
        const download = file.children.find((item) => item.id === "download");
        await download.execute(env);
        assert.verifySteps(["/spreadsheet/xlsx"]);
    });

    QUnit.test("Can make a copy", async function (assert) {
        const serverData = getBasicServerData();
        const spreadsheet = serverData.models["documents.document"].records[1];
        const { env, model } = await createSpreadsheet({
            spreadsheetId: spreadsheet.id,
            serverData,
            mockRPC: async function (route, args) {
                if (args.method === "copy" && args.model === "documents.document") {
                    assert.step("copy");
                    assert.equal(
                        args.kwargs.default.spreadsheet_snapshot,
                        false,
                        "It should reset the snapshot"
                    );
                    assert.deepEqual(
                        args.kwargs.default.spreadsheet_revision_ids,
                        [],
                        "It should reset the revisions"
                    );
                    assert.equal(
                        args.kwargs.default.spreadsheet_data,
                        JSON.stringify(model.exportData()),
                        "It should copy the data"
                    );
                    return 1;
                }
            },
        });
        const file = topbarMenuRegistry.getAll().find((item) => item.id === "file");
        const makeCopy = file.children.find((item) => item.id === "make_copy");
        makeCopy.execute(env);
        assert.verifySteps(["copy"]);
    });

    QUnit.test("Lazy load currencies", async function (assert) {
        const { env } = await createSpreadsheet({
            mockRPC: async function (route, args) {
                if (args.method === "search_read" && args.model === "res.currency") {
                    assert.step("currencies-loaded");
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
        assert.verifySteps([]);
        const menuPath = ["format", "format_number", "format_custom_currency"];
        await doMenuAction(topbarMenuRegistry, menuPath, env);
        await nextTick();
        await click(document.querySelector(".o-sidePanelClose"));
        await doMenuAction(topbarMenuRegistry, menuPath, env);
        await nextTick();
        assert.verifySteps(["currencies-loaded"]);
    });

    QUnit.test("Can Insert odoo formulas from Insert > Functions > Odoo", async function (assert) {
        const { model } = await createSpreadsheet();

        setCellContent(model, "A1", `Hi :)`);

        await click(document.querySelector(".o-topbar-menu[data-id='insert']"));
        await click(document.querySelector(".o-menu-item[data-name='insert_function']"));
        await click(document.querySelector(".o-menu-root[title='Odoo']"));
        await click(document.querySelector(".o-menu-item[title='ODOO.CURRENCY.RATE']"));

        await triggerEvent(document.activeElement, null, "keydown", { key: "Enter" });

        assert.equal(getCellContent(model, "A1"), "=ODOO.CURRENCY.RATE()");
    });
});
