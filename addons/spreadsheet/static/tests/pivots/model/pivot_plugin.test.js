import { Deferred } from "@web/core/utils/concurrency";
import { animationFrame } from "@odoo/hoot-mock";
import {
    MockServer,
    makeServerError,
    patchTranslations,
    serverState,
} from "@web/../tests/web_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import {
    defineSpreadsheetActions,
    defineSpreadsheetModels,
    getBasicServerData,
} from "@spreadsheet/../tests/helpers/data";

import {
    getCell,
    getCellContent,
    getCellFormula,
    getCellValue,
    getEvaluatedCell,
} from "@spreadsheet/../tests/helpers/getters";
import { createSpreadsheetWithPivot } from "@spreadsheet/../tests/helpers/pivot";
import { CommandResult } from "@spreadsheet/o_spreadsheet/cancelled_reason";
import {
    addGlobalFilter,
    setCellContent,
    updatePivot,
} from "@spreadsheet/../tests/helpers/commands";
import { createModelWithDataSource } from "@spreadsheet/../tests/helpers/model";

import { user } from "@web/core/user";

import { Model } from "@odoo/o-spreadsheet";
import { THIS_YEAR_GLOBAL_FILTER } from "@spreadsheet/../tests/helpers/global_filter";

import * as spreadsheet from "@odoo/o-spreadsheet";
import { waitForDataLoaded } from "@spreadsheet/helpers/model";
const { DEFAULT_LOCALE } = spreadsheet.constants;
const { toZone } = spreadsheet.helpers;

describe.current.tags("headless");
defineSpreadsheetModels();
defineSpreadsheetActions();

test("can get a pivotId from cell formula", async function () {
    const { model } = await createSpreadsheetWithPivot({
        arch: /* xml */ `
                <pivot>
                    <field name="product_id" type="col"/>
                    <field name="foo" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
    });
    const sheetId = model.getters.getActiveSheetId();
    const pivotId = model.getters.getPivotIdFromPosition({ sheetId, col: 2, row: 2 });
    expect(pivotId).toBe(model.getters.getPivotId("1"));
});

test("can get a pivotId from cell formula with '-' before the formula", async function () {
    const { model } = await createSpreadsheetWithPivot({
        arch: /* xml */ `
                <pivot>
                    <field name="product_id" type="col"/>
                    <field name="foo" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
    });
    model.dispatch("SET_VALUE", {
        xc: "C3",
        text: `=-PIVOT.VALUE("1","probability","bar","false","foo","2")`,
    });
    const sheetId = model.getters.getActiveSheetId();
    const pivotId = model.getters.getPivotIdFromPosition({ sheetId, col: 2, row: 2 });
    expect(pivotId).toBe(model.getters.getPivotId("1"));
});

test("can get a pivotId from cell formula with other numerical values", async function () {
    const { model } = await createSpreadsheetWithPivot({
        arch: /* xml */ `
                <pivot>
                    <field name="product_id" type="col"/>
                    <field name="foo" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
    });
    model.dispatch("SET_VALUE", {
        xc: "C3",
        text: `=3*PIVOT.VALUE("1","probability","bar","false","foo","2")+2`,
    });
    const sheetId = model.getters.getActiveSheetId();
    const pivotId = model.getters.getPivotIdFromPosition({ sheetId, col: 2, row: 2 });
    expect(pivotId).toBe(model.getters.getPivotId("1"));
});

test("can get a pivotId from cell formula where pivot is in a function call", async function () {
    const { model } = await createSpreadsheetWithPivot({
        arch: /* xml */ `
            <pivot>
                <field name="product_id" type="col"/>
                <field name="foo" type="row"/>
                <field name="probability" type="measure"/>
            </pivot>`,
    });
    model.dispatch("SET_VALUE", {
        xc: "C3",
        text: `=SUM(PIVOT.VALUE("1","probability","bar","false","foo","2"),PIVOT.VALUE("1","probability","bar","false","foo","2"))`,
    });
    const sheetId = model.getters.getActiveSheetId();
    const pivotId = model.getters.getPivotIdFromPosition({ sheetId, col: 2, row: 2 });
    expect(pivotId).toBe(model.getters.getPivotId("1"));
});

test("can get a pivotId from cell formula where the id is a reference", async function () {
    const { model } = await createSpreadsheetWithPivot();
    setCellContent(model, "C3", `=PIVOT.VALUE(G10,"probability","bar","false","foo","2")+2`);
    setCellContent(model, "G10", "1");
    const sheetId = model.getters.getActiveSheetId();
    const pivotId = model.getters.getPivotIdFromPosition({ sheetId, col: 2, row: 2 });
    expect(pivotId).toBe(model.getters.getPivotId("1"));
});

test("can get a Pivot from cell formula where the id is a reference in an inactive sheet", async function () {
    const { model } = await createSpreadsheetWithPivot();
    const firstSheetId = model.getters.getActiveSheetId();
    model.dispatch("CREATE_SHEET", { sheetId: "2" });
    model.dispatch("ACTIVATE_SHEET", { sheetIdFrom: firstSheetId, sheetIdTo: "2" });
    setCellContent(model, "A1", "1");
    setCellContent(model, "A2", '=PIVOT.VALUE(A1,"probability")');
    model.dispatch("ACTIVATE_SHEET", { sheetIdFrom: "2", sheetIdTo: firstSheetId });
    const pivotId = model.getters.getPivotIdFromPosition({ sheetId: "2", col: 0, row: 1 });
    expect(pivotId).toBe("PIVOT#1");
});

test("can get a pivotId from cell formula (Mix of test scenarios above)", async function () {
    const { model } = await createSpreadsheetWithPivot({
        arch: /*xml*/ `
                    <pivot>
                        <field name="product_id" type="col"/>
                        <field name="foo" type="row"/>
                        <field name="probability" type="measure"/>
                    </pivot>`,
    });
    model.dispatch("SET_VALUE", {
        xc: "C3",
        text: `=3*SUM(PIVOT.VALUE("1","probability","bar","false","foo","2"),PIVOT.VALUE("1","probability","bar","false","foo","2"))+2*PIVOT.VALUE("1","probability","bar","false","foo","2")`,
    });
    const sheetId = model.getters.getActiveSheetId();
    const pivotId = model.getters.getPivotIdFromPosition({ sheetId, col: 2, row: 2 });
    expect(pivotId).toBe(model.getters.getPivotId("1"));
});

test("Can remove a pivot with undo after editing a cell", async function () {
    const { model } = await createSpreadsheetWithPivot();
    expect(getCellContent(model, "B1").startsWith("=PIVOT.HEADER")).toBe(true);
    setCellContent(model, "G10", "should be undoable");
    model.dispatch("REQUEST_UNDO");
    expect(getCellContent(model, "G10")).toBe("");
    // 2 REQUEST_UNDO because of the AUTORESIZE feature
    model.dispatch("REQUEST_UNDO");
    model.dispatch("REQUEST_UNDO");
    expect(getCellContent(model, "B1")).toBe("");
    expect(model.getters.getPivotIds().length).toBe(0);
});

test("rename pivot with empty name is refused", async () => {
    const { model, pivotId } = await createSpreadsheetWithPivot();
    const result = model.dispatch("RENAME_PIVOT", {
        pivotId,
        name: "",
    });
    expect(result.reasons).toEqual([CommandResult.EmptyName]);
});

test("rename pivot with incorrect id is refused", async () => {
    const { model } = await createSpreadsheetWithPivot();
    const result = model.dispatch("RENAME_PIVOT", {
        pivotId: "invalid",
        name: "name",
    });
    expect(result.reasons).toEqual([CommandResult.PivotIdNotFound]);
});

test("Undo/Redo for RENAME_PIVOT", async function () {
    const { model, pivotId } = await createSpreadsheetWithPivot();
    expect(model.getters.getPivotName(pivotId)).toBe("Partner Pivot");
    model.dispatch("RENAME_PIVOT", { pivotId, name: "test" });
    expect(model.getters.getPivotName(pivotId)).toBe("test");
    model.dispatch("REQUEST_UNDO");
    expect(model.getters.getPivotName(pivotId)).toBe("Partner Pivot");
    model.dispatch("REQUEST_REDO");
    expect(model.getters.getPivotName(pivotId)).toBe("test");
});

test("Can delete pivot", async function () {
    const { model, pivotId } = await createSpreadsheetWithPivot();
    model.dispatch("REMOVE_PIVOT", { pivotId });
    expect(model.getters.getPivotIds().length).toBe(0);
    const B4 = getEvaluatedCell(model, "B4");
    expect(B4.message).toBe(`There is no pivot with id "1"`);
    expect(B4.value).toBe(`#ERROR`);
});

test("Can undo/redo a delete pivot", async function () {
    const { model, pivotId } = await createSpreadsheetWithPivot();
    const value = getEvaluatedCell(model, "B4").value;
    model.dispatch("REMOVE_PIVOT", { pivotId });
    model.dispatch("REQUEST_UNDO");
    await animationFrame();
    expect(model.getters.getPivotIds().length).toBe(1);
    let B4 = getEvaluatedCell(model, "B4");
    expect(B4.value).toBe(value);
    model.dispatch("REQUEST_REDO");
    expect(model.getters.getPivotIds().length).toBe(0);
    B4 = getEvaluatedCell(model, "B4");
    expect(B4.message).toBe(`There is no pivot with id "1"`);
    expect(B4.value).toBe(`#ERROR`);
});

test("Format header displays an error for non-existing field", async function () {
    const { model } = await createSpreadsheetWithPivot();
    setCellContent(model, "G10", `=PIVOT.HEADER("1", "measure", "non-existing")`);
    setCellContent(model, "G11", `=PIVOT.HEADER("1", "non-existing", "bla")`);
    await animationFrame();
    expect(getCellValue(model, "G10")).toBe("#ERROR");
    expect(getCellValue(model, "G11")).toBe("#ERROR");
    expect(getEvaluatedCell(model, "G10").message).toBe("Field non-existing does not exist");
    expect(getEvaluatedCell(model, "G11").message).toBe("Field non-existing does not exist");
});

test("invalid group dimensions", async function () {
    const { model } = await createSpreadsheetWithPivot({
        arch: /*xml*/ `
                <pivot>
                    <field name="product_id" type="row"/>
                    <field name="foo" type="col"/>
                    <field name="bar" type="col"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
    });
    const invalids = [
        '=PIVOT.VALUE(1,"probability", "product_id", 1, "bar", false, "foo", 1)', // inverted col dimensions
        '=PIVOT.VALUE(1,"probability", "product_id", 1, "bar", false, "f"&"oo", 1)', // inverted col dimensions, "foo" computed
        '=PIVOT.VALUE(1,"probability", "product_id", 1, "bar", false)', // missing first col dimension
        '=PIVOT.VALUE(1,"probability", "#product_id", 1, "#bar", 1, "#foo", 1)',
        '=PIVOT.VALUE(1,"probability", "bar", false, "foo", 1, "product_id", 1)', // columns before rows

        '=PIVOT.HEADER(1, "product_id", 1, "bar", false, "foo", 1)', // inverted col dimensions
        '=PIVOT.HEADER(1, "product_id", 1, "bar", false)', // missing first col dimension
        '=PIVOT.HEADER(1, "#product_id", 1, "#bar", 1, "#foo", 1)',
        '=PIVOT.HEADER(1, "bar", false, "foo", 1, "product_id", 47)', // columns before rows
    ];
    for (const formula of invalids) {
        setCellContent(model, "G10", formula);
        expect(getCellValue(model, "G10")).toBe("#ERROR", { message: formula });
        expect(getEvaluatedCell(model, "G10").message).toBe(
            "Dimensions don't match the pivot definition",
            { message: formula }
        );
    }
});

test("user context is combined with pivot context to fetch data", async function () {
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
                    A1: { content: `=PIVOT.VALUE(1, "probability")` },
                },
            },
        ],
        pivots: {
            1: {
                type: "ODOO",
                columns: [{ name: "foo" }],
                domain: [],
                measures: [{ name: "probability" }],
                model: "partner",
                rows: [{ name: "bar" }],
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
                case "read_group":
                    expect.step("read_group");
                    expect(kwargs.context).toEqual(expectedFetchContext, {
                        message: "read_group",
                    });
                    break;
            }
        },
    });
    await waitForDataLoaded(model);
    expect.verifySteps(["read_group", "read_group", "read_group", "read_group"]);
});

test("Context is purged from PivotView related keys", async function (assert) {
    const spreadsheetData = {
        sheets: [
            {
                id: "sheet1",
                cells: {
                    A1: { content: `=ODOO.PIVOT(1, "probability")` },
                },
            },
        ],
        pivots: {
            1: {
                type: "ODOO",
                columns: [{ name: "foo" }],
                rows: [{ name: "bar" }],
                domain: [],
                measures: [{ name: "probability" }],
                model: "partner",
                context: {
                    pivot_measures: ["__count"],
                    // inverse row and col group bys
                    pivot_row_groupby: ["test"],
                    pivot_column_groupby: ["check"],
                    dummyKey: "true",
                },
            },
        },
    };

    const model = await createModelWithDataSource({
        spreadsheetData,
        mockRPC: function (route, { model, method, kwargs }) {
            if (model === "partner" && method === "read_group") {
                expect.step(`pop`);
                const hasBadKeys = [
                    "pivot_measures",
                    "pivot_row_groupby",
                    "pivot_column_groupby",
                ].some((val) => val in (kwargs.context || {}));
                expect(hasBadKeys).not.toBe(true);
            }
        },
    });
    await waitForDataLoaded(model);
    expect.verifySteps(["pop", "pop", "pop", "pop"]);
});

test("fetch metadata only once per model", async function () {
    const spreadsheetData = {
        sheets: [
            {
                id: "sheet1",
                cells: {
                    A1: { content: `=PIVOT.VALUE(1, "probability")` },
                    A2: { content: `=PIVOT.VALUE(2, "probability")` },
                },
            },
        ],
        pivots: {
            1: {
                type: "ODOO",
                columns: [{ name: "foo" }],
                domain: [],
                measures: [{ name: "probability", aggregator: "sum" }],
                model: "partner",
                rows: [{ name: "bar" }],
                context: {},
            },
            2: {
                type: "ODOO",
                columns: [{ name: "bar" }],
                domain: [],
                measures: [{ field: "probability", operator: "max" }],
                model: "partner",
                rows: [{ name: "foo" }],
                context: {},
            },
        },
    };
    const model = await createModelWithDataSource({
        spreadsheetData,
        mockRPC: function (route, { model, method, kwargs }) {
            if (model === "partner" && method === "fields_get") {
                expect.step(`${model}/${method}`);
            } else if (model === "ir.model" && method === "search_read") {
                expect.step(`${model}/${method}`);
            }
        },
    });
    await waitForDataLoaded(model);
    expect.verifySteps(["partner/fields_get"]);
});

test("don't fetch pivot data if no formula use it", async function () {
    const spreadsheetData = {
        pivots: {
            1: {
                type: "ODOO",
                columns: [{ name: "foo" }],
                domain: [],
                measures: [{ name: "probability", aggregator: "sum" }],
                model: "partner",
                rows: [{ name: "bar" }],
            },
        },
    };
    const model = await createModelWithDataSource({
        spreadsheetData,
        mockRPC: function (route, { model, method, kwargs }) {
            if (!["partner", "ir.model"].includes(model)) {
                return;
            }
            expect.step(`${model}/${method}`);
        },
    });
    expect.verifySteps([]);
    setCellContent(model, "A1", `=PIVOT.VALUE("1", "probability")`);
    expect(getCellValue(model, "A1")).toBe("Loading...");
    await animationFrame();
    expect.verifySteps([
        "partner/fields_get",
        "partner/read_group",
        "partner/read_group",
        "partner/read_group",
        "partner/read_group",
    ]);
    expect(getCellValue(model, "A1")).toBe(131);
});

test("evaluates only once when two pivots are loading", async function () {
    const spreadsheetData = {
        sheets: [{ id: "sheet1" }],
        pivots: {
            1: {
                type: "ODOO",
                columns: [{ name: "foo" }],
                domain: [],
                measures: [{ name: "probability", aggregator: "sum" }],
                model: "partner",
                rows: [{ name: "bar" }],
            },
            2: {
                type: "ODOO",
                columns: [{ name: "foo" }],
                domain: [],
                measures: [{ name: "probability", aggregator: "sum" }],
                model: "partner",
                rows: [{ name: "bar" }],
            },
        },
    };
    const model = await createModelWithDataSource({
        spreadsheetData,
    });
    model.config.custom.odooDataProvider.addEventListener("data-source-updated", () =>
        expect.step("data-source-notified")
    );
    setCellContent(model, "A1", '=PIVOT.VALUE("1", "probability")');
    setCellContent(model, "A2", '=PIVOT.VALUE("2", "probability")');
    expect(getCellValue(model, "A1")).toBe("Loading...");
    expect(getCellValue(model, "A2")).toBe("Loading...");
    await animationFrame();
    expect(getCellValue(model, "A1")).toBe(131);
    expect(getCellValue(model, "A2")).toBe(131);
    // evaluation after both pivots are loaded
    expect.verifySteps(["data-source-notified"]);
});

test("concurrently load the same pivot twice", async function () {
    const spreadsheetData = {
        sheets: [{ id: "sheet1" }],
        pivots: {
            1: {
                type: "ODOO",
                columns: [{ name: "foo" }],
                domain: [],
                measures: [{ name: "probability", aggregator: "sum" }],
                model: "partner",
                rows: [{ name: "bar" }],
            },
        },
    };
    const model = await createModelWithDataSource({
        spreadsheetData,
    });
    // the data loads first here, when we insert the first pivot function
    setCellContent(model, "A1", '=PIVOT.VALUE("1", "probability")');
    expect(getCellValue(model, "A1")).toBe("Loading...");
    // concurrently reload the same pivot
    model.dispatch("REFRESH_ALL_DATA_SOURCES");
    await animationFrame();
    expect(getCellValue(model, "A1")).toBe(131);
});

test("display loading while data is not fully available", async function () {
    const metadataPromise = new Deferred();
    const dataPromise = new Deferred();
    const spreadsheetData = {
        sheets: [
            {
                id: "sheet1",
                cells: {
                    A1: { content: `=PIVOT.HEADER(1, "measure", "probability")` },
                    A2: { content: `=PIVOT.HEADER(1, "product_id", 37)` },
                    A3: { content: `=PIVOT.VALUE(1, "probability")` },
                },
            },
        ],
        pivots: {
            1: {
                type: "ODOO",
                columns: [{ name: "product_id" }],
                domain: [],
                measures: [{ name: "probability", aggregator: "sum" }],
                model: "partner",
                rows: [],
            },
        },
    };
    const model = await createModelWithDataSource({
        spreadsheetData,
        mockRPC: async function (route, args, performRPC) {
            const { model, method, kwargs } = args;
            const result = MockServer.current.callOrm(args);
            if (model === "partner" && method === "fields_get") {
                expect.step(`${model}/${method}`);
                await metadataPromise;
            }
            if (
                model === "partner" &&
                method === "read_group" &&
                kwargs.groupby[0] === "product_id"
            ) {
                expect.step(`${model}/${method}`);
                await dataPromise;
            }
            if (model === "product" && method === "read") {
                expect(false).toBe(true, {
                    message: "should not be called because data is put in cache",
                });
            }
            return result;
        },
    });
    expect(getCellValue(model, "A1")).toBe("Loading...");
    expect(getCellValue(model, "A2")).toBe("Loading...");
    expect(getCellValue(model, "A3")).toBe("Loading...");
    metadataPromise.resolve();
    await animationFrame();
    setCellContent(model, "A10", "1"); // trigger a new evaluation (might also be caused by other async formulas resolving)
    expect(getCellValue(model, "A1")).toBe("Loading...");
    expect(getCellValue(model, "A2")).toBe("Loading...");
    expect(getCellValue(model, "A3")).toBe("Loading...");
    dataPromise.resolve();
    await animationFrame();
    setCellContent(model, "A10", "2");
    expect(getCellValue(model, "A1")).toBe("Probability");
    expect(getCellValue(model, "A2")).toBe("xphone");
    expect(getCellValue(model, "A3")).toBe(131);
    expect.verifySteps(["partner/fields_get", "partner/read_group"]);
});

test("pivot grouped by char field which represents numbers", async function () {
    const serverData = getBasicServerData();
    serverData.models.partner.records = [
        { name: "111", probability: 11 },
        { name: "000111", probability: 15 },
        { name: "14.0", probability: 16 },
    ];

    const { model } = await createSpreadsheetWithPivot({
        serverData,
        arch: /*xml*/ `
                <pivot>
                    <field name="name" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
    });
    expect(getCell(model, "A3").content).toBe('=PIVOT.HEADER(1,"name","000111")');
    expect(getCell(model, "A4").content).toBe('=PIVOT.HEADER(1,"name","111")');
    expect(getCell(model, "A5").content).toBe('=PIVOT.HEADER(1,"name","14.0")');
    expect(getEvaluatedCell(model, "A3").value).toBe("000111");
    expect(getEvaluatedCell(model, "A4").value).toBe("111");
    expect(getEvaluatedCell(model, "A5").value).toBe("14.0");
    expect(getCell(model, "B3").content).toBe('=PIVOT.VALUE(1,"probability","name","000111")');
    expect(getCell(model, "B4").content).toBe('=PIVOT.VALUE(1,"probability","name","111")');
    expect(getCell(model, "B5").content).toBe('=PIVOT.VALUE(1,"probability","name","14.0")');
    expect(getEvaluatedCell(model, "B3").value).toBe(15);
    expect(getEvaluatedCell(model, "B4").value).toBe(11);
    expect(getEvaluatedCell(model, "B5").value).toBe(16);
});

test("relational PIVOT.HEADER with missing id", async function () {
    const { model } = await createSpreadsheetWithPivot({
        arch: /*xml*/ `
                <pivot>
                    <field name="product_id" type="col"/>
                    <field name="bar" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
    });
    const sheetId = model.getters.getActiveSheetId();
    model.dispatch("UPDATE_CELL", {
        col: 4,
        row: 9,
        content: `=PIVOT.HEADER("1", "product_id", "1111111")`,
        sheetId,
    });
    await waitForDataLoaded(model);
    expect(getEvaluatedCell(model, "E10").message).toBe(
        "Unable to fetch the label of 1111111 of model product"
    );
});

test("relational PIVOT.HEADER with undefined id", async function () {
    const { model } = await createSpreadsheetWithPivot({
        arch: /*xml*/ `
                <pivot>
                    <field name="foo" type="col"/>
                    <field name="product_id" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
    });
    setCellContent(model, "F10", `=PIVOT.HEADER("1", "product_id", A25)`);
    expect(getCell(model, "A25")).toBe(undefined, { message: "the cell should be empty" });
    await waitForDataLoaded(model);
    const F10 = getEvaluatedCell(model, "F10");
    expect(F10.value).toBe("#ERROR");
    expect(F10.message).toBe("Unable to fetch the label of 0 of model product");
});

test("Verify pivot measures are correctly computed :)", async function () {
    const { model } = await createSpreadsheetWithPivot();
    expect(getCellValue(model, "B4")).toBe(11);
    expect(getCellValue(model, "C3")).toBe(15);
    expect(getCellValue(model, "D4")).toBe(10);
    expect(getCellValue(model, "E4")).toBe(95);
});

test("__count measure", async function () {
    const { model } = await createSpreadsheetWithPivot({
        arch: /*xml*/ `
                <pivot>
                    <field name="product_id" type="row"/>
                    <field name="__count" type="measure"/>
                </pivot>`,
    });
    setCellContent(model, "F10", '=PIVOT.VALUE(1, "__count")');
    const F10 = getEvaluatedCell(model, "F10");
    expect(F10.value).toBe(4);
    expect(F10.format).toBe("0");
});

test("invalid pivot measure", async function () {
    const { model } = await createSpreadsheetWithPivot({
        arch: /* xml */ `
                <pivot>
                    <field name="product_id" type="col"/>
                    <field name="foo" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
    });
    const formula = '=PIVOT.VALUE(1, "count")';
    setCellContent(model, "F10", formula);
    expect(getCellValue(model, "F10")).toBe("#ERROR", { message: formula });
    expect(getEvaluatedCell(model, "F10").message).toBe(
        "The argument count is not a valid measure. Here are the measures: (probability)",
        { message: formula }
    );
});

test("aggregate to 0", async function () {
    const serverData = getBasicServerData();
    serverData.models.partner.records = [
        { id: 1, name: "A", probability: 10 },
        { id: 2, name: "B", probability: -10 },
    ];

    const { model } = await createSpreadsheetWithPivot({
        serverData,
        arch: /*xml*/ `
                <pivot>
                    <field name="name" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
    });
    setCellContent(model, "A1", '=PIVOT.VALUE(1, "probability", "name", "A")');
    setCellContent(model, "A2", '=PIVOT.VALUE(1, "probability", "name", "B")');
    setCellContent(model, "A3", '=PIVOT.VALUE(1, "probability")');
    expect(getEvaluatedCell(model, "A1").value).toBe(10);
    expect(getEvaluatedCell(model, "A2").value).toBe(-10);
    expect(getEvaluatedCell(model, "A3").value).toBe(0);
});

test("pivot formula for total should return empty string instead of 'FALSE' when pivot doesn't match any data", async function () {
    const serverData = getBasicServerData();
    serverData.models.partner.records = [{ id: 1, name: "A", probability: 10 }];

    const { model } = await createSpreadsheetWithPivot({
        serverData,
        arch: /*xml*/ `
                <pivot>
                    <field name="name" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
    });

    const [pivotId] = model.getters.getPivotIds();
    model.dispatch("UPDATE_PIVOT", {
        pivotId,
        pivot: {
            ...model.getters.getPivotCoreDefinition(pivotId),
            domain: [["probability", "=", 100]],
        },
    });
    await waitForDataLoaded(model);

    setCellContent(model, "A1", '=PIVOT.VALUE(1, "probability", "name", "A")');
    setCellContent(model, "A2", '=PIVOT.VALUE(1, "probability")');
    expect(getEvaluatedCell(model, "A1").value).toBe("");
    expect(getEvaluatedCell(model, "A2").value).toBe("");

    model.dispatch("UPDATE_PIVOT", {
        pivotId,
        pivot: {
            ...model.getters.getPivotCoreDefinition(pivotId),
            domain: [],
        },
    });
    await waitForDataLoaded(model);

    expect(getEvaluatedCell(model, "A1").value).toBe(10);
    expect(getEvaluatedCell(model, "A2").value).toBe(10);
});

test("can import/export sorted pivot", async () => {
    const spreadsheetData = {
        pivots: {
            1: {
                type: "ODOO",
                columns: [{ name: "foo" }],
                domain: [],
                measures: [{ name: "probability", aggregator: "sum" }],
                model: "partner",
                rows: [{ name: "bar" }],
                sortedColumn: {
                    measure: "probability",
                    order: "asc",
                    groupId: [[], [1]],
                },
                name: "A pivot",
                context: {},
                fieldMatching: {},
                formulaId: "1",
            },
        },
    };
    const model = await createModelWithDataSource({ spreadsheetData });
    expect(model.getters.getPivotCoreDefinition(1).sortedColumn).toEqual({
        measure: "probability",
        order: "asc",
        groupId: [[], [1]],
    });
    expect(model.exportData().pivots).toEqual(spreadsheetData.pivots);
});

test("can import (export) contextual domain", async () => {
    const uid = user.userId;
    const spreadsheetData = {
        pivots: {
            1: {
                type: "ODOO",
                columns: [],
                domain: '[("foo", "=", uid)]',
                measures: [{ name: "probability", aggregator: "sum" }],
                model: "partner",
                rows: [],
                name: "A pivot",
            },
        },
    };
    const model = await createModelWithDataSource({
        spreadsheetData,
        mockRPC: function (route, args) {
            if (args.method === "read_group") {
                expect(args.kwargs.domain).toEqual([["foo", "=", uid]]);
                expect.step("read_group");
            }
        },
    });
    setCellContent(model, "A1", '=PIVOT.VALUE(1, "probability")'); // load the data (and check the rpc domain)
    await animationFrame();
    expect(model.exportData().pivots[1].domain).toBe('[("foo", "=", uid)]', {
        message: "the domain is exported with the dynamic parts",
    });
    expect.verifySteps(["read_group"]);
});

test("Can group by many2many field ", async () => {
    const { model } = await createSpreadsheetWithPivot({
        arch: /* xml */ `
            <pivot>
                <field name="foo" type="col"/>
                <field name="tag_ids" type="row"/>
                <field name="probability" type="measure"/>
            </pivot>`,
    });
    expect(getCellFormula(model, "A3")).toBe('=PIVOT.HEADER(1,"tag_ids",42)');
    expect(getCellFormula(model, "A4")).toBe('=PIVOT.HEADER(1,"tag_ids",67)');
    expect(getCellFormula(model, "A5")).toBe('=PIVOT.HEADER(1,"tag_ids",FALSE)');

    expect(getCellFormula(model, "B3")).toBe('=PIVOT.VALUE(1,"probability","tag_ids",42,"foo",1)');
    expect(getCellFormula(model, "B4")).toBe('=PIVOT.VALUE(1,"probability","tag_ids",67,"foo",1)');
    expect(getCellFormula(model, "B5")).toBe(
        '=PIVOT.VALUE(1,"probability","tag_ids",FALSE,"foo",1)'
    );

    expect(getCellFormula(model, "C3")).toBe('=PIVOT.VALUE(1,"probability","tag_ids",42,"foo",2)');
    expect(getCellFormula(model, "C4")).toBe('=PIVOT.VALUE(1,"probability","tag_ids",67,"foo",2)');
    expect(getCellFormula(model, "C5")).toBe(
        '=PIVOT.VALUE(1,"probability","tag_ids",FALSE,"foo",2)'
    );

    expect(getCellValue(model, "A3")).toBe("isCool");
    expect(getCellValue(model, "A4")).toBe("Growing");
    expect(getCellValue(model, "A5")).toBe("None");
    expect(getCellValue(model, "B3")).toBe(11);
    expect(getCellValue(model, "B4")).toBe(11);
    expect(getCellValue(model, "B5")).toBe("");
    expect(getCellValue(model, "C3")).toBe(15);
    expect(getCellValue(model, "C4")).toBe("");
    expect(getCellValue(model, "C5")).toBe("");
});

test("PIVOT.HEADER grouped by date field without value", async function () {
    const { model, pivotId } = await createSpreadsheetWithPivot({
        arch: /* xml */ `
                <pivot>
                    <field name="date" interval="year" type="col"/>
                    <field name="foo" type="measure"/>
                </pivot>`,
    });
    for (const granularity of ["day", "week", "month", "quarter"]) {
        updatePivot(model, pivotId, {
            columns: [{ name: "date", granularity, order: "asc" }],
        });
        await animationFrame();
        setCellContent(model, "A1", `=PIVOT.HEADER(1, "date:${granularity}", "false")`);
        expect(getCellValue(model, "A1")).toBe("None");
    }
});

test("PIVOT functions can accept spreadsheet dates", async function () {
    const { model } = await createSpreadsheetWithPivot({
        arch: /* xml */ `
            <pivot>
                <field name="date" interval="quarter" type="col"/>
                <field name="probability" type="measure"/>
            </pivot>`,
    });
    setCellContent(model, "A1", '=PIVOT.HEADER(1, "date:quarter",DATE(2016, 4, 1))');
    expect(getCellValue(model, "A1")).toBe("Q2 2016");

    setCellContent(model, "A1", '=PIVOT.VALUE(1, "probability", "date:quarter",DATE(2016, 4, 1))');
    expect(getCellValue(model, "A1")).toBe(10);

    // not the first day of the quarter
    setCellContent(model, "A1", '=PIVOT.VALUE(1, "probability", "date:quarter",DATE(2016, 4, 2))');
    expect(getCellValue(model, "A1")).toBe(10);
});

test("PIVOT formulas are correctly formatted at evaluation", async function () {
    const { model } = await createSpreadsheetWithPivot({
        arch: /* xml */ `
                <pivot>
                    <field name="product_id" type="col"/>
                    <field name="name" type="row"/>
                    <field name="foo" type="measure"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
    });
    expect(getEvaluatedCell(model, "B3").format).toBe("0");
    expect(getEvaluatedCell(model, "C3").format).toBe("#,##0.00");
});

test("PIVOT formulas with monetary measure are correctly formatted at evaluation", async function () {
    const { model } = await createSpreadsheetWithPivot({
        arch: /* xml */ `
                <pivot>
                    <field name="product_id" type="col"/>
                    <field name="name" type="row"/>
                    <field name="pognon" type="measure"/>
                </pivot>`,
    });
    expect(getEvaluatedCell(model, "B3").format).toBe("#,##0.00[$€]");
});

test("PIVOT day_of_month are correctly formatted at evaluation", async function () {
    const { model, pivotId } = await createSpreadsheetWithPivot({
        arch: /* xml */ `
                <pivot>
                    <field name="date" interval="day" type="col"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
    });
    updatePivot(model, pivotId, {
        columns: [{ name: "date", granularity: "day_of_month", order: "asc" }],
    });
    await animationFrame();
    setCellContent(model, "B1", `=PIVOT.HEADER(1, "date:day_of_month", 1)`);
    setCellContent(model, "B2", `=PIVOT.VALUE(1, "probability", "date:day_of_month", 11)`);
    expect(getEvaluatedCell(model, "B1").format).toBe("0");
    expect(getEvaluatedCell(model, "B1").value).toBe(1);
    expect(getEvaluatedCell(model, "B1").formattedValue).toBe("1");
    expect(getEvaluatedCell(model, "B2").format).toBe("#,##0.00");
    expect(getEvaluatedCell(model, "B2").value).toBe(15);
    expect(getEvaluatedCell(model, "B2").formattedValue).toBe("15.00");
});

test("PIVOT day are correctly formatted at evaluation", async function () {
    const { model } = await createSpreadsheetWithPivot({
        arch: /* xml */ `
                <pivot>
                    <field name="date" interval="day" type="col"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
    });
    expect(getEvaluatedCell(model, "B1").format).toBe("m/d/yyyy");
    expect(getEvaluatedCell(model, "B1").value).toBe(42474);
    expect(getEvaluatedCell(model, "B1").formattedValue).toBe("4/14/2016");
    expect(getEvaluatedCell(model, "B3").format).toBe("#,##0.00");
    expect(getEvaluatedCell(model, "B3").value).toBe(10);
    expect(getEvaluatedCell(model, "B3").formattedValue).toBe("10.00");
});

test("PIVOT iso_week_number are correctly formatted at evaluation", async function () {
    const { model, pivotId } = await createSpreadsheetWithPivot({
        arch: /* xml */ `
                <pivot>
                    <field name="date" interval="day" type="col"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
    });
    updatePivot(model, pivotId, {
        columns: [{ name: "date", granularity: "iso_week_number", order: "asc" }],
    });
    await animationFrame();
    setCellContent(model, "B1", `=PIVOT.HEADER(1, "date:iso_week_number", 1)`);
    setCellContent(model, "B2", `=PIVOT.VALUE(1, "probability", "date:iso_week_number", 15)`);
    expect(getEvaluatedCell(model, "B1").format).toBe("0");
    expect(getEvaluatedCell(model, "B1").value).toBe(1);
    expect(getEvaluatedCell(model, "B1").formattedValue).toBe("1");
    expect(getEvaluatedCell(model, "B2").format).toBe("#,##0.00");
    expect(getEvaluatedCell(model, "B2").value).toBe(10);
    expect(getEvaluatedCell(model, "B2").formattedValue).toBe("10.00");
});

test("PIVOT week are correctly formatted at evaluation", async function () {
    const { model } = await createSpreadsheetWithPivot({
        arch: /* xml */ `
                <pivot>
                    <field name="date" interval="week" type="col"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
    });
    expect(getEvaluatedCell(model, "B1").format).toBe(undefined);
    expect(getEvaluatedCell(model, "B1").value).toBe("W15 2016");
    expect(getEvaluatedCell(model, "B1").formattedValue).toBe("W15 2016");
    expect(getEvaluatedCell(model, "B3").format).toBe("#,##0.00");
    expect(getEvaluatedCell(model, "B3").value).toBe(10);
    expect(getEvaluatedCell(model, "B3").formattedValue).toBe("10.00");
});

test("PIVOT month_number are correctly formatted at evaluation", async function () {
    const { model, pivotId } = await createSpreadsheetWithPivot({
        arch: /* xml */ `
                <pivot>
                    <field name="date" interval="day" type="col"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
    });
    updatePivot(model, pivotId, {
        columns: [{ name: "date", granularity: "month_number", order: "asc" }],
    });
    await animationFrame();
    setCellContent(model, "B1", `=PIVOT.HEADER(1, "date:month_number", 1)`);
    setCellContent(model, "B2", `=PIVOT.VALUE(1, "probability", "date:month_number", 4)`);
    expect(getEvaluatedCell(model, "B1").format).toBe("0");
    expect(getEvaluatedCell(model, "B1").value).toBe("January");
    expect(getEvaluatedCell(model, "B1").formattedValue).toBe("January");
    expect(getEvaluatedCell(model, "B2").format).toBe("#,##0.00");
    expect(getEvaluatedCell(model, "B2").value).toBe(10);
    expect(getEvaluatedCell(model, "B2").formattedValue).toBe("10.00");
});

test("PIVOT month are correctly formatted at evaluation", async function () {
    const { model } = await createSpreadsheetWithPivot({
        arch: /* xml */ `
                <pivot>
                    <field name="date" interval="month" type="col"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
    });
    expect(getEvaluatedCell(model, "B1").format).toBe("mmmm yyyy");
    expect(getEvaluatedCell(model, "B1").value).toBe(42461);
    expect(getEvaluatedCell(model, "B1").formattedValue).toBe("April 2016");
    expect(getEvaluatedCell(model, "B3").format).toBe("#,##0.00");
    expect(getEvaluatedCell(model, "B3").value).toBe(10);
    expect(getEvaluatedCell(model, "B3").formattedValue).toBe("10.00");
});

test("PIVOT quarter_number are correctly formatted at evaluation", async function () {
    const { model, pivotId } = await createSpreadsheetWithPivot({
        arch: /* xml */ `
                <pivot>
                    <field name="date" interval="day" type="col"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
    });
    updatePivot(model, pivotId, {
        columns: [{ name: "date", granularity: "quarter_number", order: "asc" }],
    });
    await animationFrame();
    setCellContent(model, "B1", `=PIVOT.HEADER(1, "date:quarter_number", 1)`);
    setCellContent(model, "B2", `=PIVOT.VALUE(1, "probability", "date:quarter_number", 2)`);
    expect(getEvaluatedCell(model, "B1").format).toBe("0");
    expect(getEvaluatedCell(model, "B1").value).toBe("Q1");
    expect(getEvaluatedCell(model, "B1").formattedValue).toBe("Q1");
    expect(getEvaluatedCell(model, "B2").format).toBe("#,##0.00");
    expect(getEvaluatedCell(model, "B2").value).toBe(10);
    expect(getEvaluatedCell(model, "B2").formattedValue).toBe("10.00");
});

test("PIVOT quarter are correctly formatted at evaluation", async function () {
    const { model } = await createSpreadsheetWithPivot({
        arch: /* xml */ `
                <pivot>
                    <field name="date" interval="quarter" type="col"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
    });
    expect(getEvaluatedCell(model, "B1").format).toBe(undefined);
    expect(getEvaluatedCell(model, "B1").value).toBe("Q2 2016");
    expect(getEvaluatedCell(model, "B1").formattedValue).toBe("Q2 2016");
    expect(getEvaluatedCell(model, "B3").format).toBe("#,##0.00");
    expect(getEvaluatedCell(model, "B3").value).toBe(10);
    expect(getEvaluatedCell(model, "B3").formattedValue).toBe("10.00");
});

test("PIVOT year are correctly formatted at evaluation", async function () {
    const { model } = await createSpreadsheetWithPivot({
        arch: /* xml */ `
                <pivot>
                    <field name="date" interval="year" type="col"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
    });
    expect(getEvaluatedCell(model, "B1").format).toBe("0");
    expect(getEvaluatedCell(model, "B1").value).toBe(2016);
    expect(getEvaluatedCell(model, "B1").formattedValue).toBe("2016");
    expect(getEvaluatedCell(model, "B3").format).toBe("#,##0.00");
    expect(getEvaluatedCell(model, "B3").value).toBe(131);
    expect(getEvaluatedCell(model, "B3").formattedValue).toBe("131.00");
});

test("PIVOT.HEADER formulas are correctly formatted at evaluation", async function () {
    const { model } = await createSpreadsheetWithPivot({
        arch: /* xml */ `
                <pivot>
                    <field name="date" interval="day" type="col"/>
                    <field name="probability" type="row"/>
                    <field name="foo" type="measure"/>
                </pivot>`,
    });
    expect(getEvaluatedCell(model, "A3").format).toBe("#,##0.00");
    expect(getEvaluatedCell(model, "B1").format).toBe("m/d/yyyy");
    expect(getEvaluatedCell(model, "B2").format).toBe(undefined);
});

test("PIVOT.HEADER date formats are locale dependant", async function () {
    const { model } = await createSpreadsheetWithPivot({
        arch: /* xml */ `
                <pivot>
                    <field name="date" interval="day" type="col"/>
                    <field name="probability" type="row"/>
                    <field name="foo" type="measure"/>
                </pivot>`,
    });
    model.dispatch("UPDATE_LOCALE", {
        locale: { ...DEFAULT_LOCALE, dateFormat: "dd/mm/yyyy" },
    });
    expect(getEvaluatedCell(model, "B1").format).toBe("dd/mm/yyyy");
});

test("can edit pivot domain with UPDATE_ODOO_PIVOT_DOMAIN", async () => {
    const { model } = await createSpreadsheetWithPivot();
    const [pivotId] = model.getters.getPivotIds();
    expect(model.getters.getPivotCoreDefinition(pivotId).domain).toEqual([]);
    expect(getCellValue(model, "B4")).toBe(11);
    model.dispatch("UPDATE_ODOO_PIVOT_DOMAIN", {
        pivotId,
        domain: [["foo", "in", [55]]],
    });
    expect(model.getters.getPivotCoreDefinition(pivotId).domain).toEqual([["foo", "in", [55]]]);
    await waitForDataLoaded(model);
    expect(getCellValue(model, "B4")).toBe("");
    model.dispatch("REQUEST_UNDO");
    await waitForDataLoaded(model);
    expect(model.getters.getPivotCoreDefinition(pivotId).domain).toEqual([]);
    await waitForDataLoaded(model);
    expect(getCellValue(model, "B4")).toBe(11);
    model.dispatch("REQUEST_REDO");
    expect(model.getters.getPivotCoreDefinition(pivotId).domain).toEqual([["foo", "in", [55]]]);
    await waitForDataLoaded(model);
    expect(getCellValue(model, "B4")).toBe("");
});

test("can edit pivot domain with UPDATE_PIVOT", async () => {
    const { model, pivotId } = await createSpreadsheetWithPivot();
    expect(model.getters.getPivotCoreDefinition(pivotId).domain).toEqual([]);
    expect(getCellValue(model, "B4")).toBe(11);
    model.dispatch("UPDATE_PIVOT", {
        pivotId,
        pivot: {
            ...model.getters.getPivotCoreDefinition(pivotId),
            domain: [["foo", "in", [55]]],
        },
    });
    expect(model.getters.getPivotCoreDefinition(pivotId).domain).toEqual([["foo", "in", [55]]]);
    await waitForDataLoaded(model);
    expect(getCellValue(model, "B4")).toBe("");
    model.dispatch("REQUEST_UNDO");
    await waitForDataLoaded(model);
    expect(model.getters.getPivotCoreDefinition(pivotId).domain).toEqual([]);
    await waitForDataLoaded(model);
    expect(getCellValue(model, "B4")).toBe(11);
    model.dispatch("REQUEST_REDO");
    expect(model.getters.getPivotCoreDefinition(pivotId).domain).toEqual([["foo", "in", [55]]]);
    await waitForDataLoaded(model);
    expect(getCellValue(model, "B4")).toBe("");
});

test("updating a pivot without changing anything rejects the command", async () => {
    const { model, pivotId } = await createSpreadsheetWithPivot();
    const result = model.dispatch("UPDATE_PIVOT", {
        pivotId,
        pivot: {
            ...model.getters.getPivotCoreDefinition(pivotId),
        },
    });
    expect(result.isSuccessful).toBe(false);
});

test("edited domain is exported", async () => {
    const { model } = await createSpreadsheetWithPivot();
    const [pivotId] = model.getters.getPivotIds();
    model.dispatch("UPDATE_ODOO_PIVOT_DOMAIN", {
        pivotId,
        domain: [["foo", "in", [55]]],
    });
    expect(model.exportData().pivots[pivotId].domain).toEqual([["foo", "in", [55]]]);
});

test("can edit pivot groups", async () => {
    const { model } = await createSpreadsheetWithPivot();
    const [pivotId] = model.getters.getPivotIds();
    let definition = model.getters.getPivotCoreDefinition(pivotId);
    expect(definition.columns).toEqual([{ name: "foo" }]);
    expect(definition.rows).toEqual([{ name: "bar" }]);
    model.dispatch("UPDATE_PIVOT", {
        pivotId,
        pivot: {
            ...model.getters.getPivotCoreDefinition(pivotId),
            columns: [],
            rows: [],
        },
    });
    definition = model.getters.getPivotCoreDefinition(pivotId);
    expect(definition.columns).toEqual([]);
    expect(definition.rows).toEqual([]);
    model.dispatch("REQUEST_UNDO");
    definition = model.getters.getPivotCoreDefinition(pivotId);
    expect(definition.columns).toEqual([{ name: "foo" }]);
    expect(definition.rows).toEqual([{ name: "bar" }]);
});

test("field matching is removed when filter is deleted", async function () {
    const { model, pivotId } = await createSpreadsheetWithPivot();
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
            pivot: { [pivotId]: { chain: "product_id", type: "many2one" } },
        }
    );
    const [filter] = model.getters.getGlobalFilters();
    const matching = {
        chain: "product_id",
        type: "many2one",
    };
    expect(model.getters.getPivotFieldMatching(pivotId, filter.id)).toEqual(matching);
    expect(model.getters.getPivot(pivotId).getComputedDomain()).toEqual([
        ["product_id", "in", [41]],
    ]);
    model.dispatch("REMOVE_GLOBAL_FILTER", {
        id: filter.id,
    });
    expect(model.getters.getPivotFieldMatching(pivotId, filter.id)).toBe(undefined, {
        message: "it should have removed the pivot and its fieldMatching and datasource altogether",
    });
    expect(model.getters.getPivot(pivotId).getComputedDomain()).toEqual([]);
    model.dispatch("REQUEST_UNDO");
    expect(model.getters.getPivotFieldMatching(pivotId, filter.id)).toEqual(matching);
    expect(model.getters.getPivot(pivotId).getComputedDomain()).toEqual([
        ["product_id", "in", [41]],
    ]);
    model.dispatch("REQUEST_REDO");
    expect(model.getters.getPivotFieldMatching(pivotId, filter.id)).toBe(undefined);
    expect(model.getters.getPivot(pivotId).getComputedDomain()).toEqual([]);
});

test("Load pivot spreadsheet with models that cannot be accessed", async function () {
    let hasAccessRights = true;
    const { model } = await createSpreadsheetWithPivot({
        mockRPC: async function (route, args) {
            if (args.model === "partner" && args.method === "read_group" && !hasAccessRights) {
                throw makeServerError({ description: "ya done!" });
            }
        },
    });
    let headerCell;
    let cell;

    await waitForDataLoaded(model);
    headerCell = getEvaluatedCell(model, "A3");
    cell = getEvaluatedCell(model, "C3");
    expect(headerCell.value).toBe("No");
    expect(cell.value).toBe(15);

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

test("Can duplicate a pivot", async () => {
    const { model, pivotId } = await createSpreadsheetWithPivot();
    const matching = { chain: "product_id", type: "many2one" };
    const filter = { ...THIS_YEAR_GLOBAL_FILTER, id: "42" };
    await addGlobalFilter(model, filter, {
        pivot: { [pivotId]: matching },
    });
    model.dispatch("DUPLICATE_PIVOT", { pivotId, newPivotId: "2" });

    const pivotIds = model.getters.getPivotIds();
    expect(model.getters.getPivotIds().length).toBe(2);
    expect(model.getters.getPivotCoreDefinition(pivotIds[1])).toBe(
        model.getters.getPivotCoreDefinition(pivotId)
    );

    expect(model.getters.getPivotFieldMatching(pivotId, "42")).toEqual(matching);
    expect(model.getters.getPivotFieldMatching("2", "42")).toEqual(matching);
});

test("Duplicate pivot respects the formula id increment", async () => {
    const { model, pivotId } = await createSpreadsheetWithPivot();
    model.dispatch("DUPLICATE_PIVOT", { pivotId, newPivotId: "second" });
    model.dispatch("DUPLICATE_PIVOT", { pivotId, newPivotId: "third" });
    expect(model.getters.getPivotFormulaId("second")).toBe("2");
    expect(model.getters.getPivotFormulaId("third")).toBe("3");
});

test("Cannot duplicate unknown pivot", async () => {
    const model = new Model();
    const result = model.dispatch("DUPLICATE_PIVOT", {
        pivotId: "hello",
        newPivotId: "new",
    });
    expect(result.reasons).toEqual([CommandResult.PivotIdNotFound]);
});

test("Spreadsheet pivot table ignored by global fiter plugin", () => {
    patchTranslations();

    const model = new Model();
    model.selection.selectZone({ cell: { col: 0, row: 0 }, zone: toZone("A1:A4") });
    const pivotId = "pivot1";
    const sheetId = model.getters.getActiveSheetId();
    model.dispatch("INSERT_NEW_PIVOT", { pivotId, sheetId });
    model.dispatch("DUPLICATE_PIVOT", {
        pivotId,
        newPivotId: "new",
    });
    const pivotIds = model.getters.getPivotIds();
    const pivotDef = model.getters.getPivotCoreDefinition(pivotId);
    const dupPivotDef = model.getters.getPivotCoreDefinition(pivotIds[1]);
    expect(dupPivotDef).toEqual({ ...pivotDef, name: pivotDef.name + " (copy)" });
});

test("isPivotUnused getter", async () => {
    const { model, pivotId } = await createSpreadsheetWithPivot();
    const sheetId = model.getters.getActiveSheetId();
    expect(model.getters.isPivotUnused(pivotId)).toBe(false);

    model.dispatch("CREATE_SHEET", { sheetId: "2" });
    model.dispatch("DELETE_SHEET", { sheetId: sheetId });
    expect(model.getters.isPivotUnused(pivotId)).toBe(true);

    setCellContent(model, "A1", "=PIVOT.HEADER(1)");
    expect(model.getters.isPivotUnused(pivotId)).toBe(false);

    setCellContent(model, "A1", "=PIVOT.HEADER(A2)");
    expect(model.getters.isPivotUnused(pivotId)).toBe(true);

    setCellContent(model, "A2", "1");
    expect(model.getters.isPivotUnused(pivotId)).toBe(false);

    model.dispatch("REQUEST_UNDO", {});
    expect(model.getters.isPivotUnused(pivotId)).toBe(true);

    setCellContent(model, "A1", "=PIVOT(1)");
    expect(model.getters.isPivotUnused(pivotId)).toBe(false);
});

test("Data are fetched with the correct aggregator", async () => {
    await createSpreadsheetWithPivot({
        arch: /* xml */ `
                <pivot>
                    <field name="probability" type="measure"/>
                </pivot>`,
        mockRPC: async function (route, args) {
            if (args.method === "read_group") {
                expect(args.kwargs.fields).toEqual(["probability:avg"]);
                expect.step("read_group");
            }
        },
    });
    expect.verifySteps(["read_group"]);
});

test("changing measure aggregates", async () => {
    const { model, pivotId } = await createSpreadsheetWithPivot({
        arch: /* xml */ `
                <pivot>
                    <field name="probability" type="measure"/>
                </pivot>`,
        mockRPC: async function (route, args) {
            if (args.method === "read_group") {
                expect.step(args.kwargs.fields.join());
            }
        },
    });
    expect.verifySteps(["probability:avg"]);
    model.dispatch("UPDATE_PIVOT", {
        pivotId,
        pivot: {
            ...model.getters.getPivotCoreDefinition(pivotId),
            measures: [{ name: "probability", aggregator: "sum" }],
        },
    });
    await animationFrame();
    expect.verifySteps(["probability:sum"]);
    model.dispatch("UPDATE_PIVOT", {
        pivotId,
        pivot: {
            ...model.getters.getPivotCoreDefinition(pivotId),
            measures: [{ name: "foo", aggregator: "sum" }],
        },
    });
    await animationFrame();
    expect.verifySteps(["foo:sum"]);
});

test("many2one measures are aggregated with count_distinct by default", async () => {
    const { model, pivotId } = await createSpreadsheetWithPivot({
        arch: /* xml */ `
                <pivot>
                    <field name="probability" type="measure"/>
                </pivot>`,
        mockRPC: async function (route, args) {
            if (args.method === "read_group") {
                expect.step(args.kwargs.fields.join());
            }
        },
    });
    expect.verifySteps(["probability:avg"]);
    model.dispatch("UPDATE_PIVOT", {
        pivotId,
        pivot: {
            ...model.getters.getPivotCoreDefinition(pivotId),
            measures: [{ name: "product_id" }], // no aggregator specified
        },
    });
    setCellContent(model, "A1", '=PIVOT.VALUE(1, "product_id")');
    await animationFrame();
    expect(getEvaluatedCell(model, "A1").value).toBe(2);
    expect.verifySteps(["product_id:count_distinct"]);
});

test("changing measure aggregates changes the format", async () => {
    const { model, pivotId } = await createSpreadsheetWithPivot({
        arch: /* xml */ `
                <pivot>
                    <field name="probability" type="measure"/>
                </pivot>`,
    });
    setCellContent(model, "A1", '=PIVOT.VALUE(1, "probability")');
    expect(getEvaluatedCell(model, "A1").format).toBe("#,##0.00");
    model.dispatch("UPDATE_PIVOT", {
        pivotId,
        pivot: {
            ...model.getters.getPivotCoreDefinition(pivotId),
            measures: [{ name: "probability", aggregator: "count_distinct" }],
        },
    });
    await animationFrame();
    expect(getEvaluatedCell(model, "A1").format).toBe("0");
});

test("changing order of group by", async () => {
    const { model, pivotId } = await createSpreadsheetWithPivot({
        arch: /* xml */ `
                <pivot>
                    <field name="foo" type="col"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
        mockRPC: async function (route, args) {
            if (args.method === "read_group") {
                expect.step(args.kwargs.orderby || "NO_ORDER");
            }
        },
    });
    expect.verifySteps(["NO_ORDER", "NO_ORDER"]);
    model.dispatch("UPDATE_PIVOT", {
        pivotId,
        pivot: {
            ...model.getters.getPivotCoreDefinition(pivotId),
            columns: [{ name: "foo", order: "asc" }],
        },
    });
    expect(model.getters.getPivotCoreDefinition(pivotId).columns).toEqual([
        { name: "foo", order: "asc" },
    ]);
    await animationFrame();
    expect.verifySteps(["NO_ORDER", "foo asc"]);
    model.dispatch("UPDATE_PIVOT", {
        pivotId,
        pivot: {
            ...model.getters.getPivotCoreDefinition(pivotId),
            columns: [{ name: "foo" }],
        },
    });
    await animationFrame();
    expect.verifySteps(["NO_ORDER", "NO_ORDER"]);
});

test("change date order", async () => {
    const { model, pivotId } = await createSpreadsheetWithPivot({
        arch: /* xml */ `
                <pivot>
                    <field name="probability" type="measure"/>
                </pivot>`,
        mockRPC: async function (route, args) {
            if (args.method === "read_group") {
                expect.step(args.kwargs.orderby || "NO_ORDER");
            }
        },
    });
    expect.verifySteps(["NO_ORDER"]);
    model.dispatch("UPDATE_PIVOT", {
        pivotId,
        pivot: {
            ...model.getters.getPivotCoreDefinition(pivotId),
            columns: [
                { name: "date", granularity: "year", order: "asc" },
                { name: "date", granularity: "month", order: "desc" },
            ],
        },
    });
    await animationFrame();
    expect.verifySteps(["NO_ORDER", "date:year asc", "date:year asc,date:month desc"]);
});

test("duplicated dimension on col and row with different granularity", async () => {
    const serverData = getBasicServerData();
    serverData.models.partner.records = [{ id: 1, date: "2024-03-30", probability: 11 }];
    const { model } = await createSpreadsheetWithPivot({
        serverData,
        arch: /* xml */ `
                <pivot>
                    <field name="date" type="col" interval="year"/>
                    <field name="date" type="row" interval="month"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
    });

    setCellContent(
        model,
        "A1",
        '=PIVOT.VALUE(1,"probability","date:month","3/2024","date:year",2024)'
    );
    setCellContent(model, "A2", '=PIVOT.VALUE(1,"probability","#date:month",1,"#date:year",1)'); // positional
    expect(getEvaluatedCell(model, "A1").value).toBe(11);
    expect(getEvaluatedCell(model, "A2").value).toBe(11);
});

test("changing granularity of group by", async () => {
    const { model, pivotId } = await createSpreadsheetWithPivot({
        arch: /* xml */ `
                <pivot>
                    <field name="date" type="col"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
        mockRPC: async function (route, args) {
            if (args.method === "read_group") {
                const groupBys = args.kwargs.groupby;
                if (groupBys.length) {
                    expect.step(args.kwargs.groupby.join(","));
                }
            }
        },
    });
    expect.verifySteps(["date:month"]);
    model.dispatch("UPDATE_PIVOT", {
        pivotId,
        pivot: {
            ...model.getters.getPivotCoreDefinition(pivotId),
            columns: [{ name: "date", granularity: "day" }],
        },
    });
    expect(model.getters.getPivotCoreDefinition(pivotId).columns).toEqual([
        { name: "date", granularity: "day" },
    ]);
    await animationFrame();
    expect.verifySteps(["date:day"]);
});
