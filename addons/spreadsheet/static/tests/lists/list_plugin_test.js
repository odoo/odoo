/** @odoo-module */

import { session } from "@web/session";
import { nextTick, patchWithCleanup } from "@web/../tests/helpers/utils";
import { makeServerError } from "@web/../tests/helpers/mock_server";

import { CommandResult } from "@spreadsheet/o_spreadsheet/cancelled_reason";
import { createModelWithDataSource, waitForDataSourcesLoaded } from "../utils/model";
import { addGlobalFilter, selectCell, setCellContent } from "../utils/commands";
import {
    getBorders,
    getCell,
    getCellContent,
    getCellFormula,
    getCells,
    getCellValue,
    getEvaluatedCell,
} from "../utils/getters";
import { createSpreadsheetWithList } from "../utils/list";
import { registry } from "@web/core/registry";
import { getBasicServerData } from "../utils/data";

import * as spreadsheet from "@odoo/o-spreadsheet";

const { DEFAULT_LOCALE } = spreadsheet.constants;

QUnit.module("spreadsheet > list plugin", {}, () => {
    QUnit.test("List export", async (assert) => {
        const { model } = await createSpreadsheetWithList();
        const total = 4 + 10 * 4; // 4 Headers + 10 lines
        assert.strictEqual(Object.values(getCells(model)).length, total);
        assert.strictEqual(getCellFormula(model, "A1"), `=ODOO.LIST.HEADER(1,"foo")`);
        assert.strictEqual(getCellFormula(model, "B1"), `=ODOO.LIST.HEADER(1,"bar")`);
        assert.strictEqual(getCellFormula(model, "C1"), `=ODOO.LIST.HEADER(1,"date")`);
        assert.strictEqual(getCellFormula(model, "D1"), `=ODOO.LIST.HEADER(1,"product_id")`);
        assert.strictEqual(getCellFormula(model, "A2"), `=ODOO.LIST(1,1,"foo")`);
        assert.strictEqual(getCellFormula(model, "B2"), `=ODOO.LIST(1,1,"bar")`);
        assert.strictEqual(getCellFormula(model, "C2"), `=ODOO.LIST(1,1,"date")`);
        assert.strictEqual(getCellFormula(model, "D2"), `=ODOO.LIST(1,1,"product_id")`);
        assert.strictEqual(getCellFormula(model, "A3"), `=ODOO.LIST(1,2,"foo")`);
        assert.strictEqual(getCellFormula(model, "A11"), `=ODOO.LIST(1,10,"foo")`);
        assert.strictEqual(getCellFormula(model, "A12"), "");
    });

    QUnit.test("Return display name of selection field", async (assert) => {
        const { model } = await createSpreadsheetWithList({
            model: "documents.document",
            columns: ["handler"],
        });
        assert.strictEqual(getCellValue(model, "A2"), "Spreadsheet");
    });

    QUnit.test("Return display_name of many2one field", async (assert) => {
        const { model } = await createSpreadsheetWithList({ columns: ["product_id"] });
        assert.strictEqual(getCellValue(model, "A2"), "xphone");
    });

    QUnit.test("Boolean fields are correctly formatted", async (assert) => {
        const { model } = await createSpreadsheetWithList({ columns: ["bar"] });
        assert.strictEqual(getCellValue(model, "A2"), "TRUE");
        assert.strictEqual(getCellValue(model, "A5"), "FALSE");
    });

    QUnit.test("properties field displays property display names", async (assert) => {
        const serverData = getBasicServerData();
        serverData.models.partner.records = [
            {
                id: 45,
                partner_properties: [
                    { name: "dbfc66e0afaa6a8d", type: "date", string: "prop 1", default: false },
                    { name: "f80b6fb58d0d4c72", type: "integer", string: "prop 2", default: 0 },
                ],
            },
        ];
        const { model } = await createSpreadsheetWithList({
            serverData,
            columns: ["partner_properties"],
        });
        assert.strictEqual(getCellValue(model, "A2"), "prop 1, prop 2");
    });

    QUnit.test("Can display a field which is not in the columns", async function (assert) {
        const { model } = await createSpreadsheetWithList();
        setCellContent(model, "A1", `=ODOO.LIST(1,1,"active")`);
        assert.strictEqual(getCellValue(model, "A1"), "Loading...");
        await waitForDataSourcesLoaded(model); // Await for batching collection of missing fields
        assert.strictEqual(getCellValue(model, "A1"), true);
    });

    QUnit.test("Can remove a list with undo after editing a cell", async function (assert) {
        const { model } = await createSpreadsheetWithList();
        assert.ok(getCellContent(model, "B1").startsWith("=ODOO.LIST.HEADER"));
        setCellContent(model, "G10", "should be undoable");
        model.dispatch("REQUEST_UNDO");
        assert.equal(getCellContent(model, "G10"), "");
        model.dispatch("REQUEST_UNDO");
        assert.equal(getCellContent(model, "B1"), "");
        assert.equal(model.getters.getListIds().length, 0);
    });

    QUnit.test("List formulas are correctly formatted at evaluation", async function (assert) {
        const { model } = await createSpreadsheetWithList({
            columns: ["foo", "probability", "bar", "date", "create_date", "product_id", "pognon"],
            linesNumber: 2,
        });
        await waitForDataSourcesLoaded(model);
        assert.strictEqual(getCell(model, "A2").format, undefined);
        assert.strictEqual(getCell(model, "B2").format, undefined);
        assert.strictEqual(getCell(model, "C2").format, undefined);
        assert.strictEqual(getCell(model, "D2").format, undefined);
        assert.strictEqual(getCell(model, "E2").format, undefined);
        assert.strictEqual(getCell(model, "F2").format, undefined);
        assert.strictEqual(getCell(model, "G2").format, undefined);
        assert.strictEqual(getCell(model, "G3").format, undefined);

        assert.strictEqual(getEvaluatedCell(model, "A2").format, "0");
        assert.strictEqual(getEvaluatedCell(model, "B2").format, "#,##0.00");
        assert.strictEqual(getEvaluatedCell(model, "C2").format, undefined);
        assert.strictEqual(getEvaluatedCell(model, "D2").format, "m/d/yyyy");
        assert.strictEqual(getEvaluatedCell(model, "E2").format, "m/d/yyyy hh:mm:ss a");
        assert.strictEqual(getEvaluatedCell(model, "F2").format, undefined);
        assert.strictEqual(getEvaluatedCell(model, "G2").format, "#,##0.00[$€]");
        assert.strictEqual(getEvaluatedCell(model, "G3").format, "[$$]#,##0.00");
    });

    QUnit.test("List formulas date formats are locale dependant", async function (assert) {
        const { model } = await createSpreadsheetWithList({
            columns: ["date", "create_date"],
            linesNumber: 2,
        });
        await waitForDataSourcesLoaded(model);
        assert.strictEqual(getEvaluatedCell(model, "A2").format, "m/d/yyyy");
        assert.strictEqual(getEvaluatedCell(model, "B2").format, "m/d/yyyy hh:mm:ss a");

        const myLocale = { ...DEFAULT_LOCALE, dateFormat: "d/m/yyyy", timeFormat: "hh:mm:ss" };
        model.dispatch("UPDATE_LOCALE", { locale: myLocale });

        assert.strictEqual(getEvaluatedCell(model, "A2").format, "d/m/yyyy");
        assert.strictEqual(getEvaluatedCell(model, "B2").format, "d/m/yyyy hh:mm:ss");
    });

    QUnit.test("Json fields are not supported in list formulas", async function (assert) {
        const { model } = await createSpreadsheetWithList({
            columns: ["foo", "jsonField"],
            linesNumber: 2,
        });
        setCellContent(model, "A1", `=ODOO.LIST(1,1,"foo")`);
        setCellContent(model, "A2", `=ODOO.LIST(1,1,"jsonField")`);
        await waitForDataSourcesLoaded(model);
        assert.strictEqual(getEvaluatedCell(model, "A1").value, 12);
        assert.strictEqual(getEvaluatedCell(model, "A2").value, "#ERROR");
        assert.strictEqual(
            getEvaluatedCell(model, "A2").error.message,
            `Fields of type "json" are not supported`
        );
    });

    QUnit.test("can select a List from cell formula", async function (assert) {
        const { model } = await createSpreadsheetWithList();
        const sheetId = model.getters.getActiveSheetId();
        const listId = model.getters.getListIdFromPosition({ sheetId, col: 0, row: 0 });
        model.dispatch("SELECT_ODOO_LIST", { listId });
        const selectedListId = model.getters.getSelectedListId();
        assert.strictEqual(selectedListId, "1");
    });

    QUnit.test(
        "can select a List from cell formula with '-' before the formula",
        async function (assert) {
            const { model } = await createSpreadsheetWithList();
            setCellContent(model, "A1", `=-ODOO.LIST("1","1","foo")`);
            const sheetId = model.getters.getActiveSheetId();
            const listId = model.getters.getListIdFromPosition({ sheetId, col: 0, row: 0 });
            model.dispatch("SELECT_ODOO_LIST", { listId });
            const selectedListId = model.getters.getSelectedListId();
            assert.strictEqual(selectedListId, "1");
        }
    );
    QUnit.test(
        "can select a List from cell formula with other numerical values",
        async function (assert) {
            const { model } = await createSpreadsheetWithList();
            setCellContent(model, "A1", `=3*ODOO.LIST("1","1","foo")`);
            const sheetId = model.getters.getActiveSheetId();
            const listId = model.getters.getListIdFromPosition({ sheetId, col: 0, row: 0 });
            model.dispatch("SELECT_ODOO_LIST", { listId });
            const selectedListId = model.getters.getSelectedListId();
            assert.strictEqual(selectedListId, "1");
        }
    );

    QUnit.test("List datasource is loaded with correct linesNumber", async function (assert) {
        const { model } = await createSpreadsheetWithList({ linesNumber: 2 });
        const [listId] = model.getters.getListIds();
        const dataSource = model.getters.getListDataSource(listId);
        assert.strictEqual(dataSource.maxPosition, 2);
    });

    QUnit.test("can select a List from cell formula within a formula", async function (assert) {
        const { model } = await createSpreadsheetWithList();
        setCellContent(model, "A1", `=SUM(ODOO.LIST("1","1","foo"),1)`);
        const sheetId = model.getters.getActiveSheetId();
        const listId = model.getters.getListIdFromPosition({ sheetId, col: 0, row: 0 });
        model.dispatch("SELECT_ODOO_LIST", { listId });
        const selectedListId = model.getters.getSelectedListId();
        assert.strictEqual(selectedListId, "1");
    });

    QUnit.test(
        "can select a List from cell formula where the id is a reference",
        async function (assert) {
            const { model } = await createSpreadsheetWithList();
            setCellContent(model, "A1", `=ODOO.LIST(G10,"1","foo")`);
            setCellContent(model, "G10", "1");
            const sheetId = model.getters.getActiveSheetId();
            const listId = model.getters.getListIdFromPosition({ sheetId, col: 0, row: 0 });
            model.dispatch("SELECT_ODOO_LIST", { listId });
            const selectedListId = model.getters.getSelectedListId();
            assert.strictEqual(selectedListId, "1");
        }
    );

    QUnit.test("Referencing non-existing fields does not crash", async function (assert) {
        assert.expect(4);
        const forbiddenFieldName = "product_id";
        let spreadsheetLoaded = false;
        const { model } = await createSpreadsheetWithList({
            columns: ["bar", "product_id"],
            mockRPC: async function (route, args, performRPC) {
                if (
                    spreadsheetLoaded &&
                    args.method === "web_search_read" &&
                    args.model === "partner" &&
                    args.kwargs.specification[forbiddenFieldName]
                ) {
                    // We should not go through this condition if the forbidden fields is properly filtered
                    assert.ok(false, `${forbiddenFieldName} should have been ignored`);
                }
            },
        });
        const listId = model.getters.getListIds()[0];
        // remove forbidden field from the fields of the list.
        delete model.getters.getListDataSource(listId).getFields()[forbiddenFieldName];
        spreadsheetLoaded = true;
        model.dispatch("REFRESH_ALL_DATA_SOURCES");
        await nextTick();
        setCellContent(model, "A1", `=ODOO.LIST.HEADER("1", "${forbiddenFieldName}")`);
        setCellContent(model, "A2", `=ODOO.LIST("1","1","${forbiddenFieldName}")`);

        assert.equal(
            model.getters.getListDataSource(listId).getFields()[forbiddenFieldName],
            undefined
        );
        assert.strictEqual(getCellValue(model, "A1"), forbiddenFieldName);
        const A2 = getEvaluatedCell(model, "A2");
        assert.equal(A2.type, "error");
        assert.equal(
            A2.error.message,
            `The field ${forbiddenFieldName} does not exist or you do not have access to that field`
        );
    });

    QUnit.test("don't fetch list data if no formula use it", async function (assert) {
        const spreadsheetData = {
            lists: {
                1: {
                    id: 1,
                    columns: ["foo", "contact_name"],
                    domain: [],
                    model: "partner",
                    orderBy: [],
                    context: {},
                },
            },
        };
        const model = await createModelWithDataSource({
            spreadsheetData,
            mockRPC: function (_, { model, method }) {
                if (!["partner", "ir.model"].includes(model)) {
                    return;
                }
                assert.step(`${model}/${method}`);
            },
        });
        assert.verifySteps([]);
        setCellContent(model, "A1", `=ODOO.LIST("1", "1", "foo")`);
        /*
         * Ask a first time the value => It will trigger a loading of the data source.
         */
        assert.equal(getCellValue(model, "A1"), "Loading...");
        await nextTick();
        assert.equal(getCellValue(model, "A1"), 12);
        assert.verifySteps(["partner/fields_get", "partner/web_search_read"]);
    });

    QUnit.test("user context is combined with list context to fetch data", async function (assert) {
        const context = {
            allowed_company_ids: [15],
            tz: "bx",
            lang: "FR",
            uid: 4,
        };
        const testSession = {
            uid: 4,
            user_companies: {
                allowed_companies: {
                    15: { id: 15, name: "Hermit" },
                    16: { id: 16, name: "Craft" },
                },
                current_company: 15,
            },
            user_context: context,
        };
        const spreadsheetData = {
            sheets: [
                {
                    id: "sheet1",
                    cells: {
                        A1: { content: `=ODOO.LIST("1", "1", "name")` },
                    },
                },
            ],
            lists: {
                1: {
                    id: 1,
                    columns: ["name", "contact_name"],
                    domain: [],
                    model: "partner",
                    orderBy: [],
                    context: {
                        allowed_company_ids: [16],
                        default_stage_id: 9,
                        search_default_stage_id: 90,
                        tz: "nz",
                        lang: "EN",
                        uid: 40,
                    },
                },
            },
        };
        const expectedFetchContext = {
            allowed_company_ids: [15],
            default_stage_id: 9,
            search_default_stage_id: 90,
            tz: "bx",
            lang: "FR",
            uid: 4,
        };
        patchWithCleanup(session, testSession);
        const model = await createModelWithDataSource({
            spreadsheetData,
            mockRPC: function (route, { model, method, kwargs }) {
                if (model !== "partner") {
                    return;
                }
                switch (method) {
                    case "web_search_read":
                        assert.step("web_search_read");
                        assert.deepEqual(
                            kwargs.context,
                            expectedFetchContext,
                            "search_read context"
                        );
                        break;
                }
            },
        });
        await waitForDataSourcesLoaded(model);
        assert.verifySteps(["web_search_read"]);
    });

    QUnit.test("rename list with empty name is refused", async (assert) => {
        const { model } = await createSpreadsheetWithList();
        const result = model.dispatch("RENAME_ODOO_LIST", {
            listId: "1",
            name: "",
        });
        assert.deepEqual(result.reasons, [CommandResult.EmptyName]);
    });

    QUnit.test("rename list with incorrect id is refused", async (assert) => {
        const { model } = await createSpreadsheetWithList();
        const result = model.dispatch("RENAME_ODOO_LIST", {
            listId: "invalid",
            name: "name",
        });
        assert.deepEqual(result.reasons, [CommandResult.ListIdNotFound]);
    });

    QUnit.test("Undo/Redo for RENAME_ODOO_LIST", async function (assert) {
        assert.expect(4);
        const { model } = await createSpreadsheetWithList();
        assert.equal(model.getters.getListName("1"), "List");
        model.dispatch("RENAME_ODOO_LIST", { listId: "1", name: "test" });
        assert.equal(model.getters.getListName("1"), "test");
        model.dispatch("REQUEST_UNDO");
        assert.equal(model.getters.getListName("1"), "List");
        model.dispatch("REQUEST_REDO");
        assert.equal(model.getters.getListName("1"), "test");
    });

    QUnit.test("Can delete list", async function (assert) {
        const { model } = await createSpreadsheetWithList();
        model.dispatch("REMOVE_ODOO_LIST", { listId: "1" });
        assert.strictEqual(model.getters.getListIds().length, 0);
        const B4 = getEvaluatedCell(model, "B4");
        assert.equal(B4.error.message, `There is no list with id "1"`);
        assert.equal(B4.value, `#ERROR`);
    });

    QUnit.test("Can undo/redo a delete list", async function (assert) {
        const { model } = await createSpreadsheetWithList();
        const value = getEvaluatedCell(model, "B4").value;
        model.dispatch("REMOVE_ODOO_LIST", { listId: "1" });
        model.dispatch("REQUEST_UNDO");
        assert.strictEqual(model.getters.getListIds().length, 1);
        let B4 = getEvaluatedCell(model, "B4");
        assert.equal(B4.error, undefined);
        assert.equal(B4.value, value);
        model.dispatch("REQUEST_REDO");
        assert.strictEqual(model.getters.getListIds().length, 0);
        B4 = getEvaluatedCell(model, "B4");
        assert.equal(B4.error.message, `There is no list with id "1"`);
        assert.equal(B4.value, `#ERROR`);
    });

    QUnit.test("can edit list domain", async (assert) => {
        const { model } = await createSpreadsheetWithList();
        const [listId] = model.getters.getListIds();
        assert.deepEqual(model.getters.getListDefinition(listId).domain, []);
        assert.strictEqual(getCellValue(model, "B2"), "TRUE");
        model.dispatch("UPDATE_ODOO_LIST_DOMAIN", {
            listId,
            domain: [["foo", "in", [55]]],
        });
        assert.deepEqual(model.getters.getListDefinition(listId).domain, [["foo", "in", [55]]]);
        await waitForDataSourcesLoaded(model);
        assert.strictEqual(getCellValue(model, "B2"), "");
        model.dispatch("REQUEST_UNDO");
        await waitForDataSourcesLoaded(model);
        assert.deepEqual(model.getters.getListDefinition(listId).domain, []);
        await waitForDataSourcesLoaded(model);
        assert.strictEqual(getCellValue(model, "B2"), "TRUE");
        model.dispatch("REQUEST_REDO");
        assert.deepEqual(model.getters.getListDefinition(listId).domain, [["foo", "in", [55]]]);
        await waitForDataSourcesLoaded(model);
        assert.strictEqual(getCellValue(model, "B2"), "");
        const result = model.dispatch("UPDATE_ODOO_LIST_DOMAIN", {
            listId: "invalid",
            domain: [],
        });
        assert.deepEqual(result.reasons, [CommandResult.ListIdNotFound]);
    });

    QUnit.test("edited domain is exported", async (assert) => {
        const { model } = await createSpreadsheetWithList();
        const [listId] = model.getters.getListIds();
        model.dispatch("UPDATE_ODOO_LIST_DOMAIN", {
            listId,
            domain: [["foo", "in", [55]]],
        });
        assert.deepEqual(model.exportData().lists["1"].domain, [["foo", "in", [55]]]);
    });

    QUnit.test(
        "Cannot see record of a list in dashboard mode if wrong list formula",
        async function (assert) {
            const fakeActionService = {
                dependencies: [],
                start: (env) => ({
                    doAction: (params) => {
                        assert.step(params.res_model);
                        assert.step(params.res_id.toString());
                    },
                }),
            };
            registry.category("services").add("action", fakeActionService);
            const { model } = await createSpreadsheetWithList();
            const sheetId = model.getters.getActiveSheetId();
            model.dispatch("UPDATE_CELL", {
                col: 0,
                row: 1,
                sheetId,
                content: "=ODOO.LIST()",
            });
            model.updateMode("dashboard");
            selectCell(model, "A2");
            assert.verifySteps([]);
        }
    );

    QUnit.test("field matching is removed when filter is deleted", async function (assert) {
        const { model } = await createSpreadsheetWithList();
        await addGlobalFilter(
            model,
            {
                id: "42",
                type: "relation",
                label: "test",
                defaultValue: [41],
                modelName: undefined,
                rangeType: undefined,
            },
            {
                list: { 1: { chain: "product_id", type: "many2one" } },
            }
        );
        const [filter] = model.getters.getGlobalFilters();
        const matching = {
            chain: "product_id",
            type: "many2one",
        };
        assert.deepEqual(model.getters.getListFieldMatching("1", filter.id), matching);
        assert.deepEqual(model.getters.getListDataSource("1").getComputedDomain(), [
            ["product_id", "in", [41]],
        ]);
        model.dispatch("REMOVE_GLOBAL_FILTER", {
            id: filter.id,
        });
        assert.deepEqual(
            model.getters.getListFieldMatching("1", filter.id),
            undefined,
            "it should have removed the pivot and its fieldMatching and datasource altogether"
        );
        assert.deepEqual(model.getters.getListDataSource("1").getComputedDomain(), []);
        model.dispatch("REQUEST_UNDO");
        assert.deepEqual(model.getters.getListFieldMatching("1", filter.id), matching);
        assert.deepEqual(model.getters.getListDataSource("1").getComputedDomain(), [
            ["product_id", "in", [41]],
        ]);
        model.dispatch("REQUEST_REDO");
        assert.deepEqual(model.getters.getListFieldMatching("1", filter.id), undefined);
        assert.deepEqual(model.getters.getListDataSource("1").getComputedDomain(), []);
    });

    QUnit.test("Preload currency of monetary field", async function (assert) {
        assert.expect(3);
        await createSpreadsheetWithList({
            columns: ["pognon"],
            mockRPC: async function (route, args, performRPC) {
                if (args.method === "web_search_read" && args.model === "partner") {
                    const spec = args.kwargs.specification;
                    assert.strictEqual(Object.keys(spec).length, 2);
                    assert.deepEqual(spec.currency_id, {
                        fields: {
                            display_name: {},
                            name: {},
                            symbol: {},
                            decimal_places: {},
                            position: {},
                        },
                    });
                    assert.deepEqual(spec.pognon, {});
                }
            },
        });
    });

    QUnit.test(
        "list with both a monetary field and the related currency field",
        async function (assert) {
            const { model } = await createSpreadsheetWithList({
                columns: ["pognon", "currency_id"],
            });
            setCellContent(model, "A1", '=ODOO.LIST(1, 1, "pognon")');
            setCellContent(model, "A2", '=ODOO.LIST(1, 1, "currency_id")');
            await waitForDataSourcesLoaded(model);
            assert.strictEqual(getEvaluatedCell(model, "A1").formattedValue, "74.40€");
            assert.strictEqual(getEvaluatedCell(model, "A2").value, "EUR");
        }
    );

    QUnit.test(
        "list with both a monetary field and the related currency field",
        async function (assert) {
            const { model } = await createSpreadsheetWithList({
                columns: ["currency_id", "pognon"],
            });
            setCellContent(model, "A1", '=ODOO.LIST(1, 1, "pognon")');
            setCellContent(model, "A2", '=ODOO.LIST(1, 1, "currency_id")');
            await waitForDataSourcesLoaded(model);
            assert.strictEqual(getEvaluatedCell(model, "A1").formattedValue, "74.40€");
            assert.strictEqual(getEvaluatedCell(model, "A2").value, "EUR");
        }
    );

    QUnit.test("add currency field after the list has been loaded", async function (assert) {
        const { model } = await createSpreadsheetWithList({
            columns: ["pognon"],
        });
        setCellContent(model, "A1", '=ODOO.LIST(1, 1, "pognon")');
        await waitForDataSourcesLoaded(model);
        setCellContent(model, "A2", '=ODOO.LIST(1, 1, "currency_id")');
        assert.strictEqual(getEvaluatedCell(model, "A2").value, "EUR");
    });

    QUnit.test("Spec of web_search_read is minimal", async function (assert) {
        const spreadsheetData = {
            lists: {
                1: {
                    id: 1,
                    columns: ["currency_id", "pognon", "foo"],
                    model: "partner",
                    orderBy: [],
                },
            },
        };
        const model = await createModelWithDataSource({
            spreadsheetData,
            mockRPC: function (route, args) {
                if (args.method === "web_search_read") {
                    assert.deepEqual(args.kwargs.specification, {
                        pognon: {},
                        currency_id: {
                            fields: {
                                name: {},
                                symbol: {},
                                decimal_places: {},
                                display_name: {},
                                position: {},
                            },
                        },
                        foo: {},
                    });
                    assert.step("web_search_read");
                }
            },
        });
        setCellContent(model, "A1", '=ODOO.LIST(1, 1, "pognon")');
        setCellContent(model, "A2", '=ODOO.LIST(1, 1, "currency_id")');
        setCellContent(model, "A3", '=ODOO.LIST(1, 1, "foo")');
        await waitForDataSourcesLoaded(model);
        assert.verifySteps(["web_search_read"]);
    });

    QUnit.test(
        "List record limit is computed during the import and UPDATE_CELL",
        async function (assert) {
            const spreadsheetData = {
                sheets: [
                    {
                        id: "sheet1",
                        cells: {
                            A1: { content: `=ODOO.LIST("1", "1", "foo")` },
                        },
                    },
                ],
                lists: {
                    1: {
                        id: 1,
                        columns: ["foo", "contact_name"],
                        domain: [],
                        model: "partner",
                        orderBy: [],
                        context: {},
                    },
                },
            };
            const model = await createModelWithDataSource({ spreadsheetData });
            const ds = model.getters.getListDataSource("1");
            assert.strictEqual(ds.maxPosition, 1);
            assert.strictEqual(ds.maxPositionFetched, 1);
            setCellContent(model, "A1", `=ODOO.LIST("1", "42", "foo")`);
            assert.strictEqual(ds.maxPosition, 42);
            assert.strictEqual(ds.maxPositionFetched, 1);
            await waitForDataSourcesLoaded(model);
            assert.strictEqual(ds.maxPosition, 42);
            assert.strictEqual(ds.maxPositionFetched, 42);
        }
    );

    QUnit.test("can import (export) contextual domain", async function (assert) {
        const uid = session.user_context.uid;
        const spreadsheetData = {
            lists: {
                1: {
                    id: 1,
                    columns: ["foo", "contact_name"],
                    domain: '[("foo", "=", uid)]',
                    model: "partner",
                    orderBy: [],
                },
            },
        };
        const model = await createModelWithDataSource({
            spreadsheetData,
            mockRPC: function (route, args) {
                if (args.method === "web_search_read") {
                    assert.deepEqual(args.kwargs.domain, [["foo", "=", uid]]);
                    assert.step("web_search_read");
                }
            },
        });
        setCellContent(model, "A1", '=ODOO.LIST("1", "1", "foo")');
        await nextTick();
        assert.strictEqual(
            model.exportData().lists[1].domain,
            '[("foo", "=", uid)]',
            "the domain is exported with the dynamic parts"
        );
        assert.verifySteps(["web_search_read"]);
    });

    QUnit.test(
        "Load list spreadsheet with models that cannot be accessed",
        async function (assert) {
            let hasAccessRights = true;
            const { model } = await createSpreadsheetWithList({
                mockRPC: async function (route, args) {
                    if (
                        args.model === "partner" &&
                        args.method === "web_search_read" &&
                        !hasAccessRights
                    ) {
                        throw makeServerError({ description: "ya done!" });
                    }
                },
            });
            let headerCell;
            let cell;
            await waitForDataSourcesLoaded(model);
            headerCell = getEvaluatedCell(model, "A3");
            cell = getEvaluatedCell(model, "C3");

            assert.equal(headerCell.value, 1);
            assert.equal(cell.value, 42669);

            hasAccessRights = false;
            model.dispatch("REFRESH_ODOO_LIST", { listId: "1" });
            await waitForDataSourcesLoaded(model);
            headerCell = getEvaluatedCell(model, "A3");
            cell = getEvaluatedCell(model, "C3");

            assert.equal(headerCell.value, "#ERROR");
            assert.equal(headerCell.error.message, "ya done!");
            assert.equal(cell.value, "#ERROR");
            assert.equal(cell.error.message, "ya done!");
        }
    );

    QUnit.test("Cells in the list header zone have borders", async function (assert) {
        const { model } = await createSpreadsheetWithList({
            linesNumber: 4,
        });
        const leftBorder = { left: { style: "thin", color: "#2D7E84" } };
        const rightBorder = { right: { style: "thin", color: "#2D7E84" } };
        const topBorder = { top: { style: "thin", color: "#2D7E84" } };
        const bottomBorder = { bottom: { style: "thin", color: "#2D7E84" } };
        assert.deepEqual(getBorders(model, "A1"), { ...topBorder, ...bottomBorder, ...leftBorder });
        assert.deepEqual(getBorders(model, "B1"), { ...topBorder, ...bottomBorder });
        assert.deepEqual(getBorders(model, "D1"), {
            ...topBorder,
            ...bottomBorder,
            ...rightBorder,
        });
        assert.deepEqual(getBorders(model, "A5"), { ...leftBorder, ...bottomBorder });
        assert.deepEqual(getBorders(model, "D5"), { ...rightBorder, ...bottomBorder });
    });
});
