/* @odoo-module */

import * as spreadsheet from "@odoo/o-spreadsheet";
import { downloadFile } from "@web/core/network/download";
import {
    getFixture,
    nextTick,
    click,
    patchWithCleanup,
    triggerEvent,
} from "@web/../tests/helpers/utils";
import { contains } from "@web/../tests/utils";
import { createWebClient, doAction } from "@web/../tests/webclient/helpers";

import { getBasicData, getBasicServerData } from "@spreadsheet/../tests/utils/data";
import { prepareWebClientForSpreadsheet } from "@spreadsheet_edition/../tests/utils/webclient_helpers";
import { createSpreadsheet } from "../spreadsheet_test_utils";
import { setCellContent, selectCell, setSelection } from "@spreadsheet/../tests/utils/commands";
import { doMenuAction } from "@spreadsheet/../tests/utils/ui";
import { getCell, getCellContent, getCellValue } from "@spreadsheet/../tests/utils/getters";

const { topbarMenuRegistry } = spreadsheet.registries;
const { toZone } = spreadsheet.helpers;
const { Model } = spreadsheet;
/** @typedef {import("@spreadsheet/o_spreadsheet/o_spreadsheet").Model} Model */
let target;

export const TEST_LOCALES = [
    {
        name: "United States",
        code: "en_US",
        thousandsSeparator: ",",
        decimalSeparator: ".",
        dateFormat: "m/d/yyyy",
        timeFormat: "hh:mm:ss a",
        formulaArgSeparator: ",",
    },
    {
        name: "France",
        code: "fr_FR",
        thousandsSeparator: " ",
        decimalSeparator: ",",
        dateFormat: "dd/mm/yyyy",
        timeFormat: "hh:mm:ss",
        formulaArgSeparator: ";",
    },
    {
        name: "Odooland",
        code: "od_OO",
        thousandsSeparator: "*",
        decimalSeparator: ".",
        dateFormat: "yyyy/mm/dd",
        timeFormat: "hh:mm:ss",
        formulaArgSeparator: ",",
    },
];

QUnit.module(
    "documents_spreadsheet > Spreadsheet Client Action",
    {
        beforeEach: function () {
            target = getFixture();
        },
    },
    function () {
        QUnit.test("open spreadsheet with deprecated `active_id` params", async function (assert) {
            assert.expect(4);
            await prepareWebClientForSpreadsheet();
            const webClient = await createWebClient({
                serverData: { models: getBasicData() },
                mockRPC: async function (route, args) {
                    if (args.method === "join_spreadsheet_session") {
                        assert.step("spreadsheet-loaded");
                        assert.equal(args.args[0], 1, "It should load the correct spreadsheet");
                    }
                },
            });
            await doAction(webClient, {
                type: "ir.actions.client",
                tag: "action_open_spreadsheet",
                params: {
                    active_id: 1,
                },
            });
            assert.containsOnce(target, ".o-spreadsheet", "It should have opened the spreadsheet");
            assert.verifySteps(["spreadsheet-loaded"]);
        });

        QUnit.test("breadcrumb is rendered in control panel", async function (assert) {
            assert.expect(3);

            const actions = {
                1: {
                    id: 1,
                    name: "Documents",
                    res_model: "documents.document",
                    type: "ir.actions.act_window",
                    views: [[false, "list"]],
                },
            };
            const views = {
                "documents.document,false,list": '<tree><field name="name"/></tree>',
                "documents.document,false,search": "<search></search>",
            };
            const serverData = { actions, models: getBasicData(), views };
            await prepareWebClientForSpreadsheet();
            const webClient = await createWebClient({
                serverData,
            });
            await doAction(webClient, 1);
            await doAction(webClient, {
                type: "ir.actions.client",
                tag: "action_open_spreadsheet",
                params: {
                    spreadsheet_id: 1,
                },
            });
            assert.strictEqual(
                target.querySelector("ol.breadcrumb").textContent,
                "Documents",
                "It should display the breadcrumb"
            );
            assert.strictEqual(
                target.querySelector(".o_breadcrumb input").value,
                "My spreadsheet",
                "It should display the spreadsheet title"
            );
            assert.containsOnce(
                target,
                ".o_breadcrumb .o_spreadsheet_favorite",
                "It should display the favorite toggle button"
            );
        });

        QUnit.test("Can open a spreadsheet in readonly", async function (assert) {
            const { model } = await createSpreadsheet({
                mockRPC: async function (route, args) {
                    if (args.method === "join_spreadsheet_session") {
                        return {
                            data: {},
                            name: "name",
                            revisions: [],
                            isReadonly: true,
                        };
                    }
                },
            });
            assert.ok(model.getters.isReadonly());
        });

        QUnit.test("format menu with default currency", async function (assert) {
            const { model, env } = await createSpreadsheet({
                mockRPC: async function (route, args) {
                    if (args.method === "join_spreadsheet_session") {
                        return {
                            data: {},
                            name: "name",
                            revisions: [],
                            default_currency: {
                                code: "θdoo",
                                symbol: "θ",
                                position: "after",
                                decimalPlaces: 2,
                            },
                        };
                    }
                },
            });
            await doMenuAction(
                topbarMenuRegistry,
                ["format", "format_number", "format_number_currency"],
                env
            );
            assert.equal(getCell(model, "A1").format, "#,##0.00[$θ]");
            await doMenuAction(
                topbarMenuRegistry,
                ["format", "format_number", "format_number_currency_rounded"],
                env
            );
            assert.equal(getCell(model, "A1").format, "#,##0[$θ]");
        });

        QUnit.test("dialog window not normally displayed", async function (assert) {
            assert.expect(1);
            await createSpreadsheet();
            const dialog = document.querySelector(".o_dialog");
            assert.equal(dialog, undefined, "Dialog should not normally be displayed ");
        });

        QUnit.test("notify user window", async function () {
            const { env } = await createSpreadsheet();
            env.notifyUser({ text: "this is a notification", type: "warning", sticky: true });
            await contains(".o_notification.border-warning", { text: "this is a notification" });
        });

        QUnit.test("raise error window", async function (assert) {
            assert.expect(4);
            const { env } = await createSpreadsheet();
            env.raiseError("this is a message in an opened window that requests user action");
            await nextTick();
            const dialog = document.querySelector(".o_dialog");
            assert.ok(dialog !== undefined, "Dialog can be opened");
            assert.equal(
                document.querySelector(".modal-body p").textContent,
                "this is a message in an opened window that requests user action",
                "Can set dialog content"
            );
            assert.equal(
                document.querySelector(".o_dialog_error_text"),
                null,
                "NotifyUser have no error text"
            );
            assert.equal(
                document.querySelectorAll(".modal-footer button").length,
                1,
                "NotifyUser have 1 button"
            );
        });

        QUnit.test("ask confirmation when merging", async function (assert) {
            const fixture = getFixture();
            const { model } = await createSpreadsheet();
            const sheetId = model.getters.getActiveSheetId();
            setCellContent(model, "A2", "hello");
            setSelection(model, "A1:A2");
            await nextTick();

            await click(fixture, ".o-menu-item-button[title='Merge cells']");
            const dialog = document.querySelector(".o_dialog");
            assert.ok(dialog, "Dialog should be open");
            await click(document, ".o_dialog .btn-secondary"); // cancel
            assert.equal(model.getters.isSingleCellOrMerge(sheetId, toZone("A1:A2")), false);

            await click(fixture, ".o-menu-item-button[title='Merge cells']");
            await click(document, ".o_dialog .btn-primary"); // confirm
            assert.equal(model.getters.isSingleCellOrMerge(sheetId, toZone("A1:A2")), true);
        });

        QUnit.test("Grid has still the focus after a dialog", async function (assert) {
            const { model, env } = await createSpreadsheet();
            selectCell(model, "F4");
            env.raiseError("Notification");
            await nextTick();
            await click(document, ".modal-footer .btn-primary");
            await nextTick();
            assert.strictEqual(document.activeElement, document.querySelector(".o-grid div.o-composer"));
        });

        QUnit.test("convert data from template", async function (assert) {
            const data = {
                sheets: [
                    {
                        id: "sheet1",
                        cells: {
                            A1: {
                                content:
                                    '=ODOO.PIVOT(1,"probability","foo", ODOO.PIVOT.POSITION(1, "foo", 1))',
                            },
                        },
                    },
                ],
                pivots: {
                    1: {
                        id: 1,
                        colGroupBys: ["foo"],
                        domain: [],
                        measures: [{ field: "probability" }],
                        model: "partner",
                        rowGroupBys: ["bar"],
                        context: {},
                    },
                },
            };
            const serverData = getBasicServerData();
            serverData.models["documents.document"].records.push({
                id: 3000,
                name: "My template spreadsheet",
                spreadsheet_data: JSON.stringify(data),
            });
            const { model } = await createSpreadsheet({
                spreadsheetId: 3000,
                serverData,
                convert_from_template: true,
                mockRPC: function (route, { method, model, args }) {
                    if (model === "documents.document" && method === "write") {
                        assert.step("reset data");
                        const data = JSON.parse(args[1].spreadsheet_data);
                        assert.deepEqual(
                            data.sheets[0].cells.A1.content,
                            '=ODOO.PIVOT(1,"probability","foo","1")'
                        );
                    }
                },
            });
            assert.strictEqual(
                getCellContent(model, "A1"),
                '=ODOO.PIVOT(1,"probability","foo","1")'
            );
            await nextTick();
            assert.verifySteps(["reset data"]);
        });

        QUnit.test("menu > download as json", async function (assert) {
            let downloadedData = null;
            patchWithCleanup(downloadFile, {
                _download: (data, fileName) => {
                    assert.step("download");
                    assert.ok(data.includes("Hello World"));
                    assert.ok(data.includes("A3"));
                    assert.strictEqual(fileName, "My spreadsheet.osheet.json");
                    downloadedData = data;
                },
            });

            const serverData = getBasicServerData();
            const spreadsheet = serverData.models["documents.document"].records[1];
            spreadsheet.name = "My spreadsheet";
            spreadsheet.spreadsheet_data = JSON.stringify({
                sheets: [{ cells: { A3: { content: "Hello World" } } }],
            });

            const { env, model } = await createSpreadsheet({
                spreadsheetId: spreadsheet.id,
                serverData,
            });

            assert.strictEqual(getCellValue(model, "A3"), "Hello World");

            await doMenuAction(topbarMenuRegistry, ["file", "download_as_json"], env);
            assert.verifySteps(["download"]);

            const modelFromLoadedJSON = new Model(JSON.parse(downloadedData));
            assert.strictEqual(getCellValue(modelFromLoadedJSON, "A3"), "Hello World");
        });

        QUnit.test("Spreadsheet is created with locale in data", async function (assert) {
            const serverData = getBasicServerData();
            serverData.models["documents.document"].records.push({
                id: 3000,
                name: "My template spreadsheet",
                spreadsheet_data: JSON.stringify({ settings: { locale: TEST_LOCALES[1] } }),
            });

            const { model } = await createSpreadsheet({ serverData, spreadsheetId: 3000 });
            assert.deepEqual(model.getters.getLocale().code, "fr_FR");
        });

        QUnit.test("Odoo locales are displayed in setting side panel", async function (assert) {
            const { env } = await createSpreadsheet({
                mockRPC: function (route, { method, model }) {
                    if (method === "get_locales_for_spreadsheet") {
                        return TEST_LOCALES;
                    }
                },
            });

            env.openSidePanel("Settings", {});
            await nextTick();

            const loadedLocales = [];
            const options = document.querySelectorAll(".o-settings-panel select option");
            for (const option of options) {
                loadedLocales.push(option.value);
            }

            assert.deepEqual(loadedLocales, ["en_US", "fr_FR", "od_OO"]);
        });

        QUnit.test("sheetName should not be left empty", async function (assert) {
            const fixture = getFixture();
            await createSpreadsheet();

            const sheetName = fixture.querySelector(".o-sheet-list .o-sheet-name");
            await triggerEvent(fixture, ".o-sheet-list .o-sheet-name", "dblclick");
            await nextTick();
            assert.ok(fixture.querySelector(".o-sheet-name-editable"));

            sheetName.innerText = "";
            await triggerEvent(fixture, ".o-sheet-list .o-sheet-name", "keydown", { key: "Enter" });
            await nextTick();
            const dialog = document.querySelector(".o_dialog");
            assert.ok(dialog, "dialog should be visible");

            await click(document, ".o_dialog .btn-primary");
            assert.ok(fixture.querySelector(".o-sheet-name-editable"));
        });
    }
);
