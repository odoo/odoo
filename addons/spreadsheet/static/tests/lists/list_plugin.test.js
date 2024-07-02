import { describe, expect, test } from "@odoo/hoot";
import { makeServerError, mockService, serverState } from "@web/../tests/web_test_helpers";
import { user } from "@web/core/user";

import {
    addGlobalFilter,
    selectCell,
    setCellContent,
} from "@spreadsheet/../tests/helpers/commands";
import {
    getBorders,
    getCell,
    getCellContent,
    getCellFormula,
    getCellValue,
    getCells,
    getEvaluatedCell,
} from "@spreadsheet/../tests/helpers/getters";
import { THIS_YEAR_GLOBAL_FILTER } from "@spreadsheet/../tests/helpers/global_filter";
import { createSpreadsheetWithList } from "@spreadsheet/../tests/helpers/list";
import { createModelWithDataSource } from "@spreadsheet/../tests/helpers/model";
import { CommandResult } from "@spreadsheet/o_spreadsheet/cancelled_reason";

import { animationFrame } from "@odoo/hoot-mock";
import * as spreadsheet from "@odoo/o-spreadsheet";
import {
    defineSpreadsheetActions,
    defineSpreadsheetModels,
    getBasicServerData,
} from "@spreadsheet/../tests/helpers/data";
import { waitForDataLoaded } from "@spreadsheet/helpers/model";
const { DEFAULT_LOCALE } = spreadsheet.constants;

describe.current.tags("headless");
defineSpreadsheetModels();
defineSpreadsheetActions();

test("List export", async () => {
    const { model } = await createSpreadsheetWithList();
    const total = 4 + 10 * 4; // 4 Headers + 10 lines
    expect(Object.values(getCells(model)).length).toBe(total);
    expect(getCellFormula(model, "A1")).toBe(`=ODOO.LIST.HEADER(1,"foo")`);
    expect(getCellFormula(model, "B1")).toBe(`=ODOO.LIST.HEADER(1,"bar")`);
    expect(getCellFormula(model, "C1")).toBe(`=ODOO.LIST.HEADER(1,"date")`);
    expect(getCellFormula(model, "D1")).toBe(`=ODOO.LIST.HEADER(1,"product_id")`);
    expect(getCellFormula(model, "A2")).toBe(`=ODOO.LIST(1,1,"foo")`);
    expect(getCellFormula(model, "B2")).toBe(`=ODOO.LIST(1,1,"bar")`);
    expect(getCellFormula(model, "C2")).toBe(`=ODOO.LIST(1,1,"date")`);
    expect(getCellFormula(model, "D2")).toBe(`=ODOO.LIST(1,1,"product_id")`);
    expect(getCellFormula(model, "A3")).toBe(`=ODOO.LIST(1,2,"foo")`);
    expect(getCellFormula(model, "A11")).toBe(`=ODOO.LIST(1,10,"foo")`);
    expect(getCellFormula(model, "A12")).toBe("");
});

test("Return display name of selection field", async () => {
    const { model } = await createSpreadsheetWithList({
        model: "res.currency",
        columns: ["position"],
    });
    expect(getCellValue(model, "A2")).toBe("A");
});

test("Return display_name of many2one field", async () => {
    const { model } = await createSpreadsheetWithList({ columns: ["product_id"] });
    expect(getCellValue(model, "A2")).toBe("xphone");
});

test("Boolean fields are correctly formatted", async () => {
    const { model } = await createSpreadsheetWithList({ columns: ["bar"] });
    expect(getCellValue(model, "A2")).toBe("TRUE");
    expect(getCellValue(model, "A5")).toBe("FALSE");
});

test("properties field displays property display names", async () => {
    const serverData = getBasicServerData();
    serverData.models.partner.records = [
        {
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
    expect(getCellValue(model, "A2")).toBe("prop 1, prop 2");
});

test("Can display a field which is not in the columns", async function () {
    const { model } = await createSpreadsheetWithList();
    setCellContent(model, "A1", `=ODOO.LIST(1,1,"active")`);
    expect(getCellValue(model, "A1")).toBe("Loading...");
    await waitForDataLoaded(model); // Await for batching collection of missing fields
    await animationFrame();
    expect(getCellValue(model, "A1")).toBe("TRUE");
});

test("Can remove a list with undo after editing a cell", async function () {
    const { model } = await createSpreadsheetWithList();
    expect(getCellContent(model, "B1").startsWith("=ODOO.LIST.HEADER")).toBe(true);
    setCellContent(model, "G10", "should be undoable");
    model.dispatch("REQUEST_UNDO");
    expect(getCellContent(model, "G10")).toBe("");
    model.dispatch("REQUEST_UNDO");
    expect(getCellContent(model, "B1")).toBe("");
    expect(model.getters.getListIds().length).toBe(0);
});

test("List formulas are correctly formatted at evaluation", async function () {
    const { model } = await createSpreadsheetWithList({
        columns: ["foo", "probability", "bar", "date", "create_date", "product_id", "pognon"],
        linesNumber: 2,
    });
    await waitForDataLoaded(model);
    expect(getCell(model, "A2").format).toBe(undefined);
    expect(getCell(model, "B2").format).toBe(undefined);
    expect(getCell(model, "C2").format).toBe(undefined);
    expect(getCell(model, "D2").format).toBe(undefined);
    expect(getCell(model, "E2").format).toBe(undefined);
    expect(getCell(model, "F2").format).toBe(undefined);
    expect(getCell(model, "G2").format).toBe(undefined);
    expect(getCell(model, "G3").format).toBe(undefined);

    expect(getEvaluatedCell(model, "A2").format).toBe("0");
    expect(getEvaluatedCell(model, "B2").format).toBe("#,##0.00");
    expect(getEvaluatedCell(model, "C2").format).toBe(undefined);
    expect(getEvaluatedCell(model, "D2").format).toBe("m/d/yyyy");
    expect(getEvaluatedCell(model, "E2").format).toBe("m/d/yyyy hh:mm:ss a");
    expect(getEvaluatedCell(model, "F2").format).toBe(undefined);
    expect(getEvaluatedCell(model, "G2").format).toBe("#,##0.00[$€]");
    expect(getEvaluatedCell(model, "G3").format).toBe("[$$]#,##0.00");
});

test("List formulas date formats are locale dependant", async function () {
    const { model } = await createSpreadsheetWithList({
        columns: ["date", "create_date"],
        linesNumber: 2,
    });
    await waitForDataLoaded(model);
    expect(getEvaluatedCell(model, "A2").format).toBe("m/d/yyyy");
    expect(getEvaluatedCell(model, "B2").format).toBe("m/d/yyyy hh:mm:ss a");

    const myLocale = { ...DEFAULT_LOCALE, dateFormat: "d/m/yyyy", timeFormat: "hh:mm:ss" };
    model.dispatch("UPDATE_LOCALE", { locale: myLocale });

    expect(getEvaluatedCell(model, "A2").format).toBe("d/m/yyyy");
    expect(getEvaluatedCell(model, "B2").format).toBe("d/m/yyyy hh:mm:ss");
});

test("Json fields are not supported in list formulas", async function () {
    const { model } = await createSpreadsheetWithList({
        columns: ["foo", "jsonField"],
        linesNumber: 2,
    });
    setCellContent(model, "A1", `=ODOO.LIST(1,1,"foo")`);
    setCellContent(model, "A2", `=ODOO.LIST(1,1,"jsonField")`);
    await waitForDataLoaded(model);
    expect(getEvaluatedCell(model, "A1").value).toBe(12);
    expect(getEvaluatedCell(model, "A2").value).toBe("#ERROR");
    expect(getEvaluatedCell(model, "A2").message).toBe(`Fields of type "json" are not supported`);
});

test("can get a listId from cell formula", async function () {
    const { model } = await createSpreadsheetWithList();
    const sheetId = model.getters.getActiveSheetId();
    const listId = model.getters.getListIdFromPosition({ sheetId, col: 0, row: 0 });
    expect(listId).toBe("1");
});

test("can get a listId from cell formula with '-' before the formula", async function () {
    const { model } = await createSpreadsheetWithList();
    setCellContent(model, "A1", `=-ODOO.LIST("1","1","foo")`);
    const sheetId = model.getters.getActiveSheetId();
    const listId = model.getters.getListIdFromPosition({ sheetId, col: 0, row: 0 });
    expect(listId).toBe("1");
});
test("can get a listId from cell formula with other numerical values", async function () {
    const { model } = await createSpreadsheetWithList();
    setCellContent(model, "A1", `=3*ODOO.LIST("1","1","foo")`);
    const sheetId = model.getters.getActiveSheetId();
    const listId = model.getters.getListIdFromPosition({ sheetId, col: 0, row: 0 });
    expect(listId).toBe("1");
});

test("List datasource is loaded with correct linesNumber", async function () {
    const { model } = await createSpreadsheetWithList({ linesNumber: 2 });
    const [listId] = model.getters.getListIds();
    const dataSource = model.getters.getListDataSource(listId);
    expect(dataSource.maxPosition).toBe(2);
});

test("can get a listId from cell formula within a formula", async function () {
    const { model } = await createSpreadsheetWithList();
    setCellContent(model, "A1", `=SUM(ODOO.LIST("1","1","foo"),1)`);
    const sheetId = model.getters.getActiveSheetId();
    const listId = model.getters.getListIdFromPosition({ sheetId, col: 0, row: 0 });
    expect(listId).toBe("1");
});

test("can get a listId from cell formula where the id is a reference", async function () {
    const { model } = await createSpreadsheetWithList();
    setCellContent(model, "A1", `=ODOO.LIST(G10,"1","foo")`);
    setCellContent(model, "G10", "1");
    const sheetId = model.getters.getActiveSheetId();
    const listId = model.getters.getListIdFromPosition({ sheetId, col: 0, row: 0 });
    expect(listId).toBe("1");
});

test("Referencing non-existing fields does not crash", async function () {
    const forbiddenFieldName = "a_field";
    let spreadsheetLoaded = false;
    const { model } = await createSpreadsheetWithList({
        columns: ["bar", "product_id"],
        mockRPC: async function (route, args) {
            if (
                spreadsheetLoaded &&
                args.method === "web_search_read" &&
                args.model === "partner" &&
                args.kwargs.specification[forbiddenFieldName]
            ) {
                // We should not go through this condition if the forbidden fields is properly filtered
                expect(false).toBe(true, {
                    message: `${forbiddenFieldName} should have been ignored`,
                });
            }
        },
    });
    const listId = model.getters.getListIds()[0];
    spreadsheetLoaded = true;
    model.dispatch("REFRESH_ALL_DATA_SOURCES");
    await animationFrame();
    setCellContent(model, "A1", `=ODOO.LIST.HEADER("1", "${forbiddenFieldName}")`);
    setCellContent(model, "A2", `=ODOO.LIST("1","1","${forbiddenFieldName}")`);

    expect(model.getters.getListDataSource(listId).getFields()[forbiddenFieldName]).toBe(undefined);
    expect(getCellValue(model, "A1")).toBe(forbiddenFieldName);
    const A2 = getEvaluatedCell(model, "A2");
    expect(A2.type).toBe("error");
    expect(A2.message).toBe(
        `The field ${forbiddenFieldName} does not exist or you do not have access to that field`
    );
});

test("don't fetch list data if no formula use it", async function () {
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
        mockRPC: function (route, { model, method }) {
            if (!["partner", "ir.model"].includes(model)) {
                return;
            }
            expect.step(`${model}/${method}`);
        },
    });
    expect.verifySteps([]);

    setCellContent(model, "A1", `=ODOO.LIST("1", "1", "foo")`);
    /*
     * Ask a first time the value => It will trigger a loading of the data source.
     */
    expect(getCellValue(model, "A1")).toBe("Loading...");
    await animationFrame();
    expect(getCellValue(model, "A1")).toBe(12);
    expect.verifySteps(["partner/fields_get", "partner/web_search_read"]);
});

test("user context is combined with list context to fetch data", async function () {
    serverState.companies = [
        { id: 15, name: "Hermit" },
        { id: 16, name: "Craft" },
    ];
    serverState.timezone = "bx";
    serverState.lang = "FR";
    serverState.userContext.allowed_company_ids = [15];

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
        uid: serverState.userId,
    };
    const model = await createModelWithDataSource({
        spreadsheetData,
        mockRPC: function (route, { model, method, kwargs }) {
            if (model !== "partner") {
                return;
            }
            switch (method) {
                case "web_search_read":
                    expect.step("web_search_read");
                    expect(kwargs.context).toEqual(expectedFetchContext);
                    break;
            }
        },
    });
    await waitForDataLoaded(model);
    expect.verifySteps(["web_search_read"]);
});

test("rename list with empty name is refused", async () => {
    const { model } = await createSpreadsheetWithList();
    const result = model.dispatch("RENAME_ODOO_LIST", {
        listId: "1",
        name: "",
    });
    expect(result.reasons).toEqual([CommandResult.EmptyName]);
});

test("rename list with incorrect id is refused", async () => {
    const { model } = await createSpreadsheetWithList();
    const result = model.dispatch("RENAME_ODOO_LIST", {
        listId: "invalid",
        name: "name",
    });
    expect(result.reasons).toEqual([CommandResult.ListIdNotFound]);
});

test("Undo/Redo for RENAME_ODOO_LIST", async function () {
    const { model } = await createSpreadsheetWithList();
    expect(model.getters.getListName("1")).toBe("List");
    model.dispatch("RENAME_ODOO_LIST", { listId: "1", name: "test" });
    expect(model.getters.getListName("1")).toBe("test");
    model.dispatch("REQUEST_UNDO");
    expect(model.getters.getListName("1")).toBe("List");
    model.dispatch("REQUEST_REDO");
    expect(model.getters.getListName("1")).toBe("test");
});

test("Can delete list", async function () {
    const { model } = await createSpreadsheetWithList();
    model.dispatch("REMOVE_ODOO_LIST", { listId: "1" });
    expect(model.getters.getListIds().length).toBe(0);
    const B4 = getEvaluatedCell(model, "B4");
    expect(B4.message).toBe('There is no list with id "1"');
    expect(B4.value).toBe("#ERROR");
});

test("Can undo/redo a delete list", async function () {
    const { model } = await createSpreadsheetWithList();
    const value = getEvaluatedCell(model, "B4").value;
    model.dispatch("REMOVE_ODOO_LIST", { listId: "1" });
    model.dispatch("REQUEST_UNDO");
    expect(model.getters.getListIds().length).toBe(1);
    let B4 = getEvaluatedCell(model, "B4");
    expect(B4.value).toBe(value);
    model.dispatch("REQUEST_REDO");
    expect(model.getters.getListIds().length).toBe(0);
    B4 = getEvaluatedCell(model, "B4");
    expect(B4.message).toBe('There is no list with id "1"');
    expect(B4.value).toBe("#ERROR");
});

test("can edit list domain", async () => {
    const { model } = await createSpreadsheetWithList();
    const [listId] = model.getters.getListIds();
    expect(model.getters.getListDefinition(listId).domain).toEqual([]);
    expect(getCellValue(model, "B2")).toBe("TRUE");
    model.dispatch("UPDATE_ODOO_LIST_DOMAIN", {
        listId,
        domain: [["foo", "in", [55]]],
    });
    expect(model.getters.getListDefinition(listId).domain).toEqual([["foo", "in", [55]]]);
    await waitForDataLoaded(model);
    expect(getCellValue(model, "B2")).toBe("");
    model.dispatch("REQUEST_UNDO");
    await waitForDataLoaded(model);
    expect(model.getters.getListDefinition(listId).domain).toEqual([]);
    await waitForDataLoaded(model);
    expect(getCellValue(model, "B2")).toBe("TRUE");
    model.dispatch("REQUEST_REDO");
    expect(model.getters.getListDefinition(listId).domain).toEqual([["foo", "in", [55]]]);
    await waitForDataLoaded(model);
    expect(getCellValue(model, "B2")).toBe("");
});

test("edited domain is exported", async () => {
    const { model } = await createSpreadsheetWithList();
    const [listId] = model.getters.getListIds();
    model.dispatch("UPDATE_ODOO_LIST_DOMAIN", {
        listId,
        domain: [["foo", "in", [55]]],
    });
    expect(model.exportData().lists["1"].domain).toEqual([["foo", "in", [55]]]);
    const result = model.dispatch("UPDATE_ODOO_LIST_DOMAIN", {
        listId: "invalid",
        domain: [],
    });
    expect(result.reasons).toEqual([CommandResult.ListIdNotFound]);
});

test("Cannot see record of a list in dashboard mode if wrong list formula", async function () {
    mockService("action", {
        async doAction(params) {
            expect.step(params.res_model);
            expect.step(params.res_id.toString());
        },
    });
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
    expect.verifySteps([]);
});

test("field matching is removed when filter is deleted", async function () {
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
    expect(model.getters.getListFieldMatching("1", filter.id)).toEqual(matching);
    expect(model.getters.getListDataSource("1").getComputedDomain()).toEqual([
        ["product_id", "in", [41]],
    ]);
    model.dispatch("REMOVE_GLOBAL_FILTER", {
        id: filter.id,
    });
    expect(model.getters.getListFieldMatching("1", filter.id)).toBe(undefined, {
        message: "it should have removed the pivot and its fieldMatching and datasource altogether",
    });
    expect(model.getters.getListDataSource("1").getComputedDomain()).toEqual([]);
    model.dispatch("REQUEST_UNDO");
    expect(model.getters.getListFieldMatching("1", filter.id)).toEqual(matching);
    expect(model.getters.getListDataSource("1").getComputedDomain()).toEqual([
        ["product_id", "in", [41]],
    ]);
    model.dispatch("REQUEST_REDO");
    expect(model.getters.getListFieldMatching("1", filter.id)).toBe(undefined);
    expect(model.getters.getListDataSource("1").getComputedDomain()).toEqual([]);
});

test("Preload currency of monetary field", async function () {
    await createSpreadsheetWithList({
        columns: ["pognon"],
        mockRPC: async function (route, args) {
            if (args.method === "web_search_read" && args.model === "partner") {
                const spec = args.kwargs.specification;
                expect(Object.keys(spec).length).toBe(2);
                expect(spec.currency_id).toEqual({
                    fields: {
                        name: {},
                        symbol: {},
                        decimal_places: {},
                        position: {},
                    },
                });
                expect(spec.pognon).toEqual({});
            }
        },
    });
});

test("fetch all and only required fields", async function () {
    const spreadsheetData = {
        sheets: [
            {
                id: "sheet1",
                cells: {
                    A1: { content: '=ODOO.LIST(1, 1, "foo")' }, // in the definition
                    A2: { content: '=ODOO.LIST(1, 1, "product_id")' }, // not in the definition
                    A3: { content: '=ODOO.LIST(1, 1, "invalid_field")' },
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
    await createModelWithDataSource({
        spreadsheetData,
        mockRPC: function (route, args) {
            if (args.method === "web_search_read" && args.model === "partner") {
                expect.step("data-fetched");
                expect(args.kwargs.specification).toEqual({
                    foo: {},
                    product_id: {
                        fields: {
                            display_name: {},
                        },
                    },
                });
            }
        },
    });
    expect.verifySteps(["data-fetched"]);
});

test("list with both a monetary field and the related currency field 1", async function () {
    const { model } = await createSpreadsheetWithList({
        columns: ["pognon", "currency_id"],
    });
    setCellContent(model, "A1", '=ODOO.LIST(1, 1, "pognon")');
    setCellContent(model, "A2", '=ODOO.LIST(1, 1, "currency_id")');
    await animationFrame();
    expect(getEvaluatedCell(model, "A1").formattedValue).toBe("74.40€");
    expect(getEvaluatedCell(model, "A2").value).toBe("EUR");
});

test("list with both a monetary field and the related currency field 2", async function () {
    const { model } = await createSpreadsheetWithList({
        columns: ["currency_id", "pognon"],
    });
    setCellContent(model, "A1", '=ODOO.LIST(1, 1, "pognon")');
    setCellContent(model, "A2", '=ODOO.LIST(1, 1, "currency_id")');
    await animationFrame();
    expect(getEvaluatedCell(model, "A1").formattedValue).toBe("74.40€");
    expect(getEvaluatedCell(model, "A2").value).toBe("EUR");
});

test("List record limit is computed during the import and UPDATE_CELL", async function () {
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
    expect(ds.maxPosition).toBe(1);
    expect(ds.maxPositionFetched).toBe(1);
    setCellContent(model, "A1", `=ODOO.LIST("1", "42", "foo")`);
    expect(ds.maxPosition).toBe(42);
    expect(ds.maxPositionFetched).toBe(1);
    await waitForDataLoaded(model);
    expect(ds.maxPosition).toBe(42);
    expect(ds.maxPositionFetched).toBe(42);
});

test("can import (export) contextual domain", async function () {
    const uid = user.userId;
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
                expect(args.kwargs.domain).toEqual([["foo", "=", uid]]);
                expect.step("web_search_read");
            }
        },
    });
    setCellContent(model, "A1", '=ODOO.LIST("1", "1", "foo")');
    await animationFrame();
    expect(model.exportData().lists[1].domain).toBe('[("foo", "=", uid)]', {
        message: "the domain is exported with the dynamic parts",
    });
    expect.verifySteps(["web_search_read"]);
});

test("Load list spreadsheet with models that cannot be accessed", async function () {
    let hasAccessRights = true;
    const { model } = await createSpreadsheetWithList({
        mockRPC: async function (route, args) {
            if (args.model === "partner" && args.method === "web_search_read" && !hasAccessRights) {
                throw makeServerError({ description: "ya done!" });
            }
        },
    });
    let headerCell;
    let cell;
    await waitForDataLoaded(model);
    headerCell = getEvaluatedCell(model, "A3");
    cell = getEvaluatedCell(model, "C3");

    expect(headerCell.value).toBe(1);
    expect(cell.value).toBe(42669);

    hasAccessRights = false;
    model.dispatch("REFRESH_ALL_DATA_SOURCES");
    await waitForDataLoaded(model);
    headerCell = getEvaluatedCell(model, "A3");
    cell = getEvaluatedCell(model, "C3");

    expect(headerCell.value).toBe("#ERROR");
    expect(headerCell.message).toBe("ya done!");
    expect(cell.value).toBe("#ERROR");
    expect(cell.message).toBe("ya done!");
});

test("Cells in the list header zone have borders", async function () {
    const { model } = await createSpreadsheetWithList({
        linesNumber: 4,
    });
    const leftBorder = { left: { style: "thin", color: "#2D7E84" } };
    const rightBorder = { right: { style: "thin", color: "#2D7E84" } };
    const topBorder = { top: { style: "thin", color: "#2D7E84" } };
    const bottomBorder = { bottom: { style: "thin", color: "#2D7E84" } };
    expect(getBorders(model, "A1")).toEqual({ ...topBorder, ...bottomBorder, ...leftBorder });
    expect(getBorders(model, "B1")).toEqual({ ...topBorder, ...bottomBorder });
    expect(getBorders(model, "D1")).toEqual({
        ...topBorder,
        ...bottomBorder,
        ...rightBorder,
    });
    expect(getBorders(model, "A5")).toEqual({ ...leftBorder, ...bottomBorder });
    expect(getBorders(model, "D5")).toEqual({ ...rightBorder, ...bottomBorder });
});

test("Can duplicate a list", async () => {
    const { model } = await createSpreadsheetWithList();
    const [listId] = model.getters.getListIds();
    const filter = { ...THIS_YEAR_GLOBAL_FILTER, id: "42" };
    const matching = { chain: "product_id", type: "many2one" };
    await addGlobalFilter(model, filter, {
        list: { [listId]: matching },
    });
    model.dispatch("DUPLICATE_ODOO_LIST", { listId, newListId: "2" });

    const listIds = model.getters.getListIds();
    expect(model.getters.getListIds().length).toBe(2);

    const expectedDuplicatedDefinition = {
        ...model.getters.getListDefinition(listId),
        id: "2",
    };
    expect(model.getters.getListDefinition(listIds[1])).toEqual(expectedDuplicatedDefinition);

    expect(model.getters.getListFieldMatching(listId, "42")).toEqual(matching);
    expect(model.getters.getListFieldMatching("2", "42")).toEqual(matching);
});

test("Cannot duplicate unknown list", async () => {
    const { model } = await createSpreadsheetWithList();
    const result = model.dispatch("DUPLICATE_ODOO_LIST", {
        listId: "hello",
        newListId: model.getters.getNextListId(),
    });
    expect(result.reasons).toEqual([CommandResult.ListIdNotFound]);
});

test("Cannot duplicate list with id different from nextId", async () => {
    const { model } = await createSpreadsheetWithList();
    const [listId] = model.getters.getListIds();
    const result = model.dispatch("DUPLICATE_ODOO_LIST", {
        listId,
        newListId: "66",
    });
    expect(result.reasons).toEqual([CommandResult.InvalidNextId]);
});

test("isListUnused getter", async () => {
    const { model } = await createSpreadsheetWithList();
    const sheetId = model.getters.getActiveSheetId();
    expect(model.getters.isListUnused("1")).toBe(false);

    model.dispatch("CREATE_SHEET", { sheetId: "2" });
    model.dispatch("DELETE_SHEET", { sheetId: sheetId });
    expect(model.getters.isListUnused("1")).toBe(true);

    setCellContent(model, "A1", '=ODOO.LIST.HEADER(1, "foo")');
    expect(model.getters.isListUnused("1")).toBe(false);

    setCellContent(model, "A1", '=ODOO.LIST.HEADER(A2, "foo")');
    expect(model.getters.isListUnused("1")).toBe(true);

    setCellContent(model, "A2", "1");
    expect(model.getters.isListUnused("1")).toBe(false);

    model.dispatch("REQUEST_UNDO", {});
    expect(model.getters.isListUnused("1")).toBe(true);
});
