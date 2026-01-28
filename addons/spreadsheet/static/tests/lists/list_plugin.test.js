import { describe, expect, test } from "@odoo/hoot";
import { makeServerError, mockService, serverState, fields } from "@web/../tests/web_test_helpers";
import { user } from "@web/core/user";

import {
    addGlobalFilter,
    redo,
    selectCell,
    setCellContent,
    undo,
} from "@spreadsheet/../tests/helpers/commands";
import {
    getCell,
    getCellContent,
    getCellFormula,
    getCellFormattedValue,
    getCells,
    getCellValue,
    getEvaluatedCell,
    getEvaluatedGrid,
    getFormattedValueGrid,
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
    generateListDefinition,
    Partner,
    Product,
    ResUsers,
    ResGroup,
    getBasicData,
} from "@spreadsheet/../tests/helpers/data";

import { waitForDataLoaded } from "@spreadsheet/helpers/model";
import { insertListInSpreadsheet } from "../helpers/list";

const { DEFAULT_LOCALE, PIVOT_STATIC_TABLE_CONFIG } = spreadsheet.constants;
const { toZone } = spreadsheet.helpers;
const { cellMenuRegistry } = spreadsheet.registries;
const Model = spreadsheet.Model;

describe.current.tags("headless");
defineSpreadsheetModels();
defineSpreadsheetActions();

test("List export", async () => {
    const { model } = await createSpreadsheetWithList();
    const total = 4 + 10 * 4; // 4 Headers + 10 lines
    expect(getCells(model).length).toBe(total);
    expect(getCellFormula(model, "A1")).toBe(`=ODOO.LIST.HEADER(1,"foo","Foo")`);
    expect(getCellFormula(model, "B1")).toBe(`=ODOO.LIST.HEADER(1,"bar","Bar")`);
    expect(getCellFormula(model, "C1")).toBe(`=ODOO.LIST.HEADER(1,"date","Date")`);
    expect(getCellFormula(model, "D1")).toBe(`=ODOO.LIST.HEADER(1,"product_id","Product")`);
    expect(getCellFormula(model, "A2")).toBe(`=ODOO.LIST.VALUE(1,1,"foo")`);
    expect(getCellFormula(model, "B2")).toBe(`=ODOO.LIST.VALUE(1,1,"bar")`);
    expect(getCellFormula(model, "C2")).toBe(`=ODOO.LIST.VALUE(1,1,"date")`);
    expect(getCellFormula(model, "D2")).toBe(`=ODOO.LIST.VALUE(1,1,"product_id")`);
    expect(getCellFormula(model, "A3")).toBe(`=ODOO.LIST.VALUE(1,2,"foo")`);
    expect(getCellFormula(model, "A11")).toBe(`=ODOO.LIST.VALUE(1,10,"foo")`);
    expect(getCellFormula(model, "A12")).toBe("");
});

test("List field name should not be empty", async () => {
    const { model } = await createSpreadsheetWithList();
    setCellContent(model, "A1", `=ODOO.LIST.VALUE(1,1,"")`);
    expect(getCellValue(model, "A1")).toBe("#ERROR");
    expect(getEvaluatedCell(model, "A1").message).toBe("The field name should not be empty.");
});

test("ODOO.LIST.HEADER with a custom header string", async () => {
    const { model } = await createSpreadsheetWithList();
    setCellContent(model, "A1", '=ODOO.LIST.HEADER(1,"foo","My custom header")');
    await waitForDataLoaded(model);
    expect(getCellValue(model, "A1")).toBe("My custom header");
});

test("Return display name of selection field", async () => {
    const { model } = await createSpreadsheetWithList({
        model: "res.currency",
        columns: [{ name: "position", string: "Position" }],
    });
    expect(getCellValue(model, "A2")).toBe("A");
});

test("Return display_name of many2one field", async () => {
    const { model } = await createSpreadsheetWithList({
        columns: [{ name: "product_id", string: "Product" }],
    });
    expect(getCellValue(model, "A2")).toBe("xphone");
});

test("Boolean fields are correctly formatted", async () => {
    const { model } = await createSpreadsheetWithList({
        columns: [{ name: "bar", string: "Bar" }],
    });
    expect(getCellValue(model, "A2")).toBe(true);
    expect(getCellValue(model, "A5")).toBe(false);
});

test("Numeric/monetary fields are correctly loaded and displayed", async () => {
    Partner._records.push({
        id: 5,
        probability: 0,
        field_with_array_agg: 0,
        currency_id: 2,
        pognon: 0,
    });
    const { model } = await createSpreadsheetWithList({
        columns: [
            { name: "pognon", string: "Money!" },
            { name: "probability", string: "Probability" },
            { name: "field_with_array_agg", string: "Array Agg" },
        ],
    });

    // prettier-ignore
    expect(getFormattedValueGrid(model, "A2:C6")).toEqual({
        A2: "74.40€",    B2: "10.00",  C2: "1",
        A3: "$74.80",    B3: "11.00",  C3: "2",
        A4: "4.00€",     B4: "95.00",  C4: "3",
        A5: "$1,000.00", B5: "15.00",  C5: "4",
        A6: "$0.00",     B6: "0.00",   C6: "0",
    });
});

test("Text fields are correctly loaded and displayed", async () => {
    Partner._records = [{ name: "Record 1" }, { name: false }];
    const { model } = await createSpreadsheetWithList({
        columns: [{ name: "name", string: "Name" }],
    });
    expect(getCellFormattedValue(model, "A2")).toBe("Record 1");
    expect(getCellFormattedValue(model, "A3")).toBe("");
});

test("cannot use property field without property name", async () => {
    Product._records = [
        {
            id: 1,
            properties_definitions: [
                { name: "dbfc66e0afaa6a8d", type: "date", string: "prop 1" },
                { name: "f80b6fb58d0d4c72", type: "integer", string: "prop 2" },
            ],
        },
    ];
    Partner._records = [
        {
            product_id: 1,
            partner_properties: {
                dbfc66e0afaa6a8d: false,
                f80b6fb58d0d4c72: 0,
            },
        },
    ];
    const { model } = await createSpreadsheetWithList({
        columns: [{ name: "partner_properties", string: "Properties" }],
    });
    expect(getEvaluatedCell(model, "A2")).toMatchObject({
        value: "#ERROR",
        message: "Please specify the property field name",
    });
});

test("Can use property fields", async () => {
    const data = getBasicData();
    data.product.records = [
        {
            id: 37,
            name: "My Product",
            properties_definitions: [
                { name: "char_property", type: "char", string: "Text" },
                { name: "date_property", type: "date", string: "Date" },
                { name: "datetime_property", type: "datetime", string: "Datetime" },
                { name: "text_property", type: "text", string: "Multiline text" },
                { name: "boolean_property", type: "boolean", string: "Boolean" },
                { name: "integer_property", type: "integer", string: "Number" },
                { name: "float_property", type: "float", string: "Decimal" },
                {
                    name: "selection_property",
                    type: "selection",
                    string: "Selection",
                    selection: [
                        ["3de00497e096656b", "option1"],
                        ["0ba4dd568840ecd5", "option2"],
                    ],
                },
                {
                    name: "tags_property",
                    tags: [
                        ["a", "A", 1],
                        ["b", "B", 2],
                        ["c", "C", 3],
                    ],
                    type: "tags",
                    string: "Tags",
                },
                {
                    name: "m2o_property",
                    type: "many2one",
                    domain: false,
                    string: "Many2one",
                    comodel: "res.currency",
                },
                {
                    name: "m2m_property",
                    type: "many2many",
                    domain: false,
                    string: "Many2many",
                    comodel: "res.currency",
                },
                { name: "signature_property", type: "signature", string: "Signature" },
                { name: "html_property", type: "html", string: "HTML" },
                {
                    name: "monetary_property",
                    type: "monetary",
                    string: "Monetary",
                    currency_field: "currency_id",
                },
            ],
        },
    ];

    const propertiesValues = {
        char_property: "CHAR",
        date_property: "2024-01-02",
        datetime_property: "2026-02-03 11:00:00",
        text_property: "LINE1\nLINE2",
        boolean_property: true,
        integer_property: 42,
        float_property: 3.14,
        selection_property: "0ba4dd568840ecd5",
        tags_property: ["a", "c"],
        m2o_property: [1, "EUR"],
        m2m_property: [
            [2, "USD"],
            [1, "EUR"],
        ],
        signature_property: "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAoAAAAHgCAYAAAD1",
        html_property: "<p>Some <strong>bold</strong> text</p>",
        monetary_property: 99.99,
    };

    data.partner.records = [
        {
            id: 1,
            product_id: 37,
            partner_properties: { ...propertiesValues },
            currency_id: 1,
        },
    ];
    const propertyField = fields.Properties({
        string: "Property char",
        definition_record: "product_id",
        definition_record_field: "properties_definitions",
    });
    Partner._fields.partner_properties = propertyField;

    const { model, env } = await createModelWithDataSource({
        serverData: { models: data },
    });

    const columns = [];
    for (const col of Object.keys(propertiesValues)) {
        const path = `partner_properties.${col}`;
        const fieldInfo = await env.services.field.loadPath("partner", path);
        columns.push({ name: path, string: fieldInfo.modelsInfo.at(-1).fieldDefs[col].string });
    }

    insertListInSpreadsheet(model, { model: "partner", columns });

    await waitForDataLoaded(model);
    expect(getEvaluatedGrid(model, "A1:A2").flat()).toEqual(["Text", "CHAR"]);
    expect(getEvaluatedGrid(model, "B1:B2").flat()).toEqual(["Date", 45293]);
    expect(getCellFormattedValue(model, "B2")).toBe("1/2/2024");
    expect(getEvaluatedGrid(model, "C1:C2").flat()).toEqual(["Datetime", 46056.5]);
    expect(getCellFormattedValue(model, "C2")).toBe("2/3/2026 12:00:00 PM");
    expect(getEvaluatedGrid(model, "D1:D2").flat()).toEqual(["Multiline text", "LINE1\nLINE2"]);
    expect(getEvaluatedGrid(model, "E1:E2").flat()).toEqual(["Boolean", true]);
    expect(getEvaluatedGrid(model, "F1:F2").flat()).toEqual(["Number", 42]);
    expect(getEvaluatedGrid(model, "G1:G2").flat()).toEqual(["Decimal", 3.14]);
    expect(getEvaluatedGrid(model, "H1:H2").flat()).toEqual(["Selection", "option2"]);
    expect(getEvaluatedGrid(model, "I1:I2").flat()).toEqual(["Tags", "A, C"]);
    expect(getEvaluatedGrid(model, "J1:J2").flat()).toEqual(["Many2one", "EUR"]);
    expect(getEvaluatedGrid(model, "K1:K2").flat()).toEqual(["Many2many", "USD, EUR"]);
    expect(getEvaluatedGrid(model, "L1:L2").flat()).toEqual([
        "Signature",
        "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAoAAAAHgCAYAAAD1",
    ]);
    expect(getEvaluatedGrid(model, "M1:M2").flat()).toEqual([
        "HTML",
        "<p>Some <strong>bold</strong> text</p>",
    ]);
    expect(getEvaluatedGrid(model, "N1:N2").flat()).toEqual(["Monetary", 99.99]);
    expect(getCellFormattedValue(model, "N2")).toBe("99.99€");
});

test("Can display a field which is not in the columns", async function () {
    const { model } = await createSpreadsheetWithList();
    setCellContent(model, "A1", `=ODOO.LIST.VALUE(1,1,"active")`);
    expect(getCellValue(model, "A1")).toBe("Loading...");
    await waitForDataLoaded(model); // Await for batching collection of missing fields
    await animationFrame();
    expect(getCellValue(model, "A1")).toBe(true);
});

test("Can remove a list with undo after editing a cell", async function () {
    const { model } = await createSpreadsheetWithList();
    expect(getCellContent(model, "B1").startsWith("=ODOO.LIST.HEADER")).toBe(true);
    setCellContent(model, "G10", "should be undoable");
    model.dispatch("REQUEST_UNDO");
    expect(getCellContent(model, "G10")).toBe("");
    model.dispatch("REQUEST_UNDO");
    expect(getCellContent(model, "B1")).toBe("");
    model.dispatch("REQUEST_UNDO");
    expect(model.getters.getListIds().length).toBe(0);
});

test("List formulas are correctly formatted at evaluation", async function () {
    const { model } = await createSpreadsheetWithList({
        columns: [
            { name: "foo", string: "Foo" },
            { name: "probability", string: "Probability" },
            { name: "bar", string: "Bar" },
            { name: "date", string: "Date" },
            { name: "create_date", string: "Create Date" },
            { name: "product_id", string: "Product" },
            { name: "pognon", string: "Pognon" },
            { name: "name", string: "Name" },
        ],
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
    expect(getCell(model, "H2").format).toBe(undefined);

    expect(getEvaluatedCell(model, "A2").format).toBe("0");
    expect(getEvaluatedCell(model, "B2").format).toBe("#,##0.00");
    expect(getEvaluatedCell(model, "C2").format).toBe(undefined);
    expect(getEvaluatedCell(model, "D2").format).toBe("m/d/yyyy");
    expect(getEvaluatedCell(model, "E2").format).toBe("m/d/yyyy hh:mm:ss a");
    expect(getEvaluatedCell(model, "F2").format).toBe(undefined);
    expect(getEvaluatedCell(model, "G2").format).toBe("#,##0.00[$€]");
    expect(getEvaluatedCell(model, "G3").format).toBe("[$$]#,##0.00");
    expect(getEvaluatedCell(model, "H2").format).toBe("@");
});

test("List formulas date formats are locale dependant", async function () {
    const { model } = await createSpreadsheetWithList({
        columns: [
            { name: "date", string: "Date" },
            { name: "create_date", string: "Creation Date" },
        ],
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
        columns: [
            { name: "foo", string: "Foo" },
            { name: "jsonField", string: "Djézonne" },
        ],
        linesNumber: 2,
    });
    setCellContent(model, "A1", `=ODOO.LIST.VALUE(1,1,"foo")`);
    setCellContent(model, "A2", `=ODOO.LIST.VALUE(1,1,"jsonField")`);
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
    setCellContent(model, "A1", `=-ODOO.LIST.VALUE("1","1","foo")`);
    const sheetId = model.getters.getActiveSheetId();
    const listId = model.getters.getListIdFromPosition({ sheetId, col: 0, row: 0 });
    expect(listId).toBe("1");
});
test("can get a listId from cell formula with other numerical values", async function () {
    const { model } = await createSpreadsheetWithList();
    setCellContent(model, "A1", `=3*ODOO.LIST.VALUE("1","1","foo")`);
    const sheetId = model.getters.getActiveSheetId();
    const listId = model.getters.getListIdFromPosition({ sheetId, col: 0, row: 0 });
    expect(listId).toBe("1");
});

test("can get a listId from a vectorized cell formula", async function () {
    const { model } = await createSpreadsheetWithList();
    const sheetId = model.getters.getActiveSheetId();
    setCellContent(model, "G1", '=LIST(1,SEQUENCE(10),"foo")');
    expect(model.getters.getListIdFromPosition({ sheetId, col: 0, row: 0 })).toBe("1");
    expect(model.getters.getListIdFromPosition({ sheetId, col: 0, row: 5 })).toBe("1");
});

test("List datasource is loaded with correct linesNumber", async function () {
    const { model } = await createSpreadsheetWithList({ linesNumber: 2 });
    const [listId] = model.getters.getListIds();
    const dataSource = model.getters.getListDataSource(listId);
    expect(dataSource.maxPosition).toBe(2);
});

test("can get a listId from cell formula within a formula", async function () {
    const { model } = await createSpreadsheetWithList();
    setCellContent(model, "A1", `=SUM(ODOO.LIST.VALUE("1","1","foo"),1)`);
    const sheetId = model.getters.getActiveSheetId();
    const listId = model.getters.getListIdFromPosition({ sheetId, col: 0, row: 0 });
    expect(listId).toBe("1");
});

test("can get a listId from cell formula where the id is a reference", async function () {
    const { model } = await createSpreadsheetWithList();
    setCellContent(model, "A1", `=ODOO.LIST.VALUE(G10,"1","foo")`);
    setCellContent(model, "G10", "1");
    const sheetId = model.getters.getActiveSheetId();
    const listId = model.getters.getListIdFromPosition({ sheetId, col: 0, row: 0 });
    expect(listId).toBe("1");
});

test("Referencing non-existing fields does not crash", async function () {
    const forbiddenFieldName = "a_field";
    let spreadsheetLoaded = false;
    const { model } = await createSpreadsheetWithList({
        columns: [
            { name: "bar", string: "Bar" },
            { name: "product_id", string: "Product" },
        ],
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
    setCellContent(model, "A2", `=ODOO.LIST.VALUE("1","1","${forbiddenFieldName}")`);

    await animationFrame();
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
                columns: [
                    { name: "foo", string: "Foo" },
                    { name: "contact_name", string: "Contact Name" },
                ],
                domain: [],
                model: "partner",
                orderBy: [],
                context: {},
            },
        },
    };
    const { model } = await createModelWithDataSource({
        spreadsheetData,
        mockRPC: function (route, { model, method }) {
            if (!["partner", "ir.model"].includes(model)) {
                return;
            }
            expect.step(`${model}/${method}`);
        },
    });
    expect.verifySteps([]);

    setCellContent(model, "A1", `=ODOO.LIST.VALUE("1", "1", "foo")`);
    /*
     * Ask a first time the value => It will trigger a loading of the data source.
     */
    expect(getCellValue(model, "A1")).toBe("Loading...");
    await animationFrame();
    expect(getCellValue(model, "A1")).toBe(12);
    expect.verifySteps(["partner/fields_get", "partner/search_count", "partner/web_search_read"]);
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
                    A1: '=ODOO.LIST.VALUE("1", "1", "name")',
                },
            },
        ],
        lists: {
            1: {
                id: 1,
                columns: [
                    { name: "name", string: "Name" },
                    { name: "contact_name", string: "Contact Name" },
                ],
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
    const { model } = await createModelWithDataSource({
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

test("can update a list", async () => {
    let spreadsheetLoaded = false;
    let isInitialUpdate = true;
    let isUndoUpdate = false;
    const { model } = await createSpreadsheetWithList({
        mockRPC: async function (route, args) {
            if (
                spreadsheetLoaded &&
                args.method === "web_search_read" &&
                args.model === "partner"
            ) {
                expect.step("data-fetched");
                if (isInitialUpdate) {
                    expect(args.kwargs.order).toBe("name DESC");
                    expect(args.kwargs.domain).toEqual([["name", "in", ["hola"]]]);
                }
                if (isUndoUpdate) {
                    expect(args.kwargs.order).toBe("");
                    expect(args.kwargs.domain).toEqual([]);
                }
            }
        },
    });
    const [listId] = model.getters.getListIds();
    spreadsheetLoaded = true;
    const listDef = model.getters.getListDefinition(listId);

    const newListDef = {
        name: "My Updated List",
        model: listDef.model,
        columns: listDef.columns,
        context: {},
        domain: [["name", "in", ["hola"]]],
        orderBy: [{ name: "name", asc: false }],
    };

    model.dispatch("UPDATE_ODOO_LIST", {
        listId,
        list: newListDef,
    });
    await waitForDataLoaded(model);
    expect.verifySteps(["data-fetched"]);
    const updatedListDef = model.getters.getListDefinition(listId);
    expect(updatedListDef).toMatchObject({
        name: newListDef.name,
        model: newListDef.model,
        columns: newListDef.columns,
        context: {},
        domain: newListDef.domain,
        orderBy: newListDef.orderBy,
    });
    isInitialUpdate = false;
    isUndoUpdate = true;
    undo(model);
    await waitForDataLoaded(model);
    expect.verifySteps(["data-fetched"]);
    expect(model.getters.getListDefinition(listId)).toEqual(listDef);
    isUndoUpdate = false;
    redo(model);
    await waitForDataLoaded(model);
    expect.verifySteps(["data-fetched"]);
    expect(model.getters.getListDefinition(listId)).toEqual(updatedListDef);
});

test("changing a column name does not trigger RPC", async () => {
    let spreadsheetLoaded = false;
    const { model } = await createSpreadsheetWithList({
        mockRPC: async function (route, args) {
            if (
                spreadsheetLoaded &&
                args.method === "web_search_read" &&
                args.model === "partner"
            ) {
                expect.step("data-fetched");
            }
        },
    });
    const [listId] = model.getters.getListIds();
    spreadsheetLoaded = true;
    const listDef = model.getters.getListDefinition(listId);
    const columns = [...listDef.columns];
    columns[0] = { ...columns[0], name: "new_field_name" };
    model.dispatch("UPDATE_ODOO_LIST", {
        listId,
        list: { ...listDef, columns },
    });
    expect.verifySteps([]);
});

test("changing a column visibility does not trigger RPC", async () => {
    let spreadsheetLoaded = false;
    const { model } = await createSpreadsheetWithList({
        mockRPC: async function (route, args) {
            if (
                spreadsheetLoaded &&
                args.method === "web_search_read" &&
                args.model === "partner"
            ) {
                expect.step("data-fetched");
            }
        },
    });
    const [listId] = model.getters.getListIds();
    spreadsheetLoaded = true;
    const listDef = model.getters.getListDefinition(listId);
    const columns = [...listDef.columns];
    columns[0] = { ...columns[0], hidden: !columns[0].hidden };
    model.dispatch("UPDATE_ODOO_LIST", {
        listId,
        list: { ...listDef, columns },
    });
    expect.verifySteps([]);
});

test("can edit list domain", async () => {
    const { model } = await createSpreadsheetWithList();
    const [listId] = model.getters.getListIds();
    expect(model.getters.getListDefinition(listId).domain).toEqual([]);
    expect(getCellValue(model, "B2")).toBe(true);
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
    expect(getCellValue(model, "B2")).toBe(true);
    model.dispatch("REQUEST_REDO");
    expect(model.getters.getListDefinition(listId).domain).toEqual([["foo", "in", [55]]]);
    await waitForDataLoaded(model);
    expect(getCellValue(model, "B2")).toBe("");
});

test("can edit list sorting", async () => {
    const { model } = await createSpreadsheetWithList({
        columns: [
            { name: "foo", string: "Foo" },
            { name: "bar", string: "Bar" },
            { name: "date", string: "Date" },
            { name: "probability", string: "Probability" },
            { name: "pognon", string: "Money!" },
        ],
    });
    // prettier-ignore
    const initialGrid = [
        ["Foo", "Bar",   "Date", "Probability", "Money!"],
        [12,     true,   42474,  10,                74.4],
        [1,      true,   42669,  11,                74.8],
        [17,     true,   42719,  95,                   4],
        [2,      false,  42715,  15,                1000],
    ]
    // prettier-ignore
    const orderedGrid = [
        ["Foo", "Bar",   "Date", "Probability", "Money!"],
        [17,     true,   42719,   95,                  4],
        [12,     true,   42474,   10,               74.4],
        [1,      true,   42669,   11,               74.8],
        [2,      false,  42715,   15,               1000],
    ]
    const [listId] = model.getters.getListIds();
    expect(model.getters.getListDefinition(listId).orderBy).toEqual([]);
    expect(getEvaluatedGrid(model, "A1:E5")).toEqual(initialGrid);
    const orderBy = [
        { name: "bar", asc: false },
        { name: "pognon", asc: true },
    ];
    const listDefinition = model.getters.getListDefinition(listId);
    model.dispatch("UPDATE_ODOO_LIST", {
        listId,
        list: {
            ...listDefinition,
            orderBy,
        },
    });
    await waitForDataLoaded(model);
    expect(model.getters.getListDefinition(listId).orderBy).toEqual(orderBy);
    expect(getEvaluatedGrid(model, "A1:E5")).toEqual(orderedGrid);
    undo(model);
    expect(model.getters.getListDefinition(listId).orderBy).toEqual([]);
    await waitForDataLoaded(model);
    expect(getEvaluatedGrid(model, "A1:E5")).toEqual(initialGrid);
    redo(model);
    await waitForDataLoaded(model);
    expect(model.getters.getListDefinition(listId).orderBy).toEqual(orderBy);
    expect(getEvaluatedGrid(model, "A1:E5")).toEqual(orderedGrid);
});

test("editing the sorting of a list of that does not exist should throw an error", async () => {
    const { model } = await createSpreadsheetWithList();
    const result = model.dispatch("UPDATE_ODOO_LIST", {
        listId: "invalid",
        list: undefined,
    });
    expect(result.reasons).toEqual([CommandResult.ListIdNotFound]);
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

test("edited list sorting is exported", async () => {
    const { model } = await createSpreadsheetWithList();
    const [listId] = model.getters.getListIds();
    const orderBy = [
        { name: "foo", asc: true },
        { name: "bar", asc: false },
    ];
    const listDefinition = model.getters.getListDefinition(listId);
    model.dispatch("UPDATE_ODOO_LIST", {
        listId,
        list: {
            ...listDefinition,
            orderBy,
        },
    });
    expect(model.exportData().lists["1"].orderBy).toEqual(orderBy);
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
        content: "=ODOO.LIST.VALUE()",
    });
    model.updateMode("dashboard");
    selectCell(model, "A2");
    expect.verifySteps([]);
});

test("Can see record with link to list cell", async function () {
    mockService("action", {
        async doAction(params) {
            expect.step(`${params.res_model},${params.res_id}`);
        },
    });
    const { model, env } = await createSpreadsheetWithList();
    model.dispatch("CREATE_SHEET", { sheetId: "42" });
    model.dispatch("ACTIVATE_SHEET", {
        sheetIdFrom: model.getters.getActiveSheetId(),
        sheetIdTo: "42",
    });
    setCellContent(model, "A1", '=ODOO.LIST.VALUE(1, 1, "foo")');
    setCellContent(model, "A2", '=ODOO.LIST.VALUE(1, 2, "foo")');

    setCellContent(model, "A3", "=A1");
    setCellContent(model, "A4", "=IF(TRUE, A2, A1)");
    const seeRecordAction = cellMenuRegistry.getAll().find((item) => item.id === "list_see_record");

    selectCell(model, "A3");
    expect(seeRecordAction.isVisible(env)).toBe(true);
    await seeRecordAction.execute(env);
    expect.verifySteps(["partner,1"]);

    selectCell(model, "A4");
    expect(seeRecordAction.isVisible(env)).toBe(true);
    await seeRecordAction.execute(env);
    expect.verifySteps(["partner,2"]);
});

test("Can see record on vectorized list index", async function () {
    mockService("action", {
        async doAction(params) {
            expect.step(`${params.res_model},${params.res_id}`);
        },
    });
    const { model, env } = await createSpreadsheetWithList();
    model.dispatch("CREATE_SHEET", { sheetId: "42" });
    model.dispatch("ACTIVATE_SHEET", {
        sheetIdFrom: model.getters.getActiveSheetId(),
        sheetIdTo: "42",
    });
    setCellContent(model, "C1", "1");
    setCellContent(model, "C2", "2");
    setCellContent(model, "D1", "3");
    setCellContent(model, "D2", "4");
    setCellContent(model, "A1", '=ODOO.LIST.VALUE(1, C1:D2, "foo")');
    const seeRecordAction = cellMenuRegistry.getAll().find((item) => item.id === "list_see_record");

    selectCell(model, "A1");
    expect(seeRecordAction.isVisible(env)).toBe(true);
    await seeRecordAction.execute(env);
    expect.verifySteps(["partner,1"]);

    selectCell(model, "A2");
    expect(seeRecordAction.isVisible(env)).toBe(true);
    await seeRecordAction.execute(env);
    expect.verifySteps(["partner,2"]);

    selectCell(model, "B1");
    expect(seeRecordAction.isVisible(env)).toBe(true);
    await seeRecordAction.execute(env);
    expect.verifySteps(["partner,3"]);

    selectCell(model, "B2");
    expect(seeRecordAction.isVisible(env)).toBe(true);
    await seeRecordAction.execute(env);
    expect.verifySteps(["partner,4"]);
});

test("field matching is removed when filter is deleted", async function () {
    const { model } = await createSpreadsheetWithList();
    await addGlobalFilter(
        model,
        {
            id: "42",
            type: "relation",
            label: "test",
            defaultValue: { operator: "in", ids: [41] },
            modelName: undefined,
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
        columns: [{ name: "pognon", string: "Pognon" }],
        mockRPC: async function (route, args) {
            if (args.method === "web_search_read" && args.model === "partner") {
                const spec = args.kwargs.specification;
                expect(Object.keys(spec).length).toBe(3);
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

test("add currency field after the list has been loaded", async function () {
    const { model } = await createSpreadsheetWithList({
        columns: [{ name: "pognon", string: "Pognon" }],
    });
    setCellContent(model, "A1", '=ODOO.LIST.VALUE(1, 1, "pognon")');
    await waitForDataLoaded(model);
    setCellContent(model, "A2", '=ODOO.LIST.VALUE(1, 1, "currency_id")');
    await waitForDataLoaded(model);
    expect(getEvaluatedCell(model, "A2").value).toBe("EUR");
});

test("fetch all and only required fields", async function () {
    const spreadsheetData = {
        sheets: [
            {
                id: "sheet1",
                cells: {
                    A1: '=ODOO.LIST.VALUE(1, 1, "foo")', // in the definition
                    A2: '=ODOO.LIST.VALUE(1, 1, "product_id")', // not in the definition
                    A3: '=ODOO.LIST.VALUE(1, 1, "invalid_field")',
                },
            },
        ],
        lists: {
            1: {
                id: 1,
                columns: [{ name: "foo" }, { name: "contact_name" }],
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
                    id: {},
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

test("fetch all required positions, including the evaluated ones", async function () {
    const spreadsheetData = {
        sheets: [
            {
                id: "sheet1",
                cells: {
                    A1: '=ODOO.LIST.VALUE(1, 11, "foo")',
                    A2: '=ODOO.LIST.VALUE(1, A3, "foo")',
                    A3: "111",
                },
            },
        ],
        lists: {
            1: {
                id: 1,
                columns: [{ name: "foo" }],
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
                expect(args.kwargs.limit).toBe(111);
            }
        },
    });
    expect.verifySteps(["data-fetched"]);
});

test("list with both a monetary field and the related currency field 1", async function () {
    const { model } = await createSpreadsheetWithList({
        columns: [
            { name: "pognon", string: "Pognon" },
            { name: "currency_id", string: "Currency" },
        ],
    });
    setCellContent(model, "A1", '=ODOO.LIST.VALUE(1, 1, "pognon")');
    setCellContent(model, "A2", '=ODOO.LIST.VALUE(1, 1, "currency_id")');
    await animationFrame();
    expect(getEvaluatedCell(model, "A1").formattedValue).toBe("74.40€");
    expect(getEvaluatedCell(model, "A2").value).toBe("EUR");
});

test("list with both a monetary field and the related currency field 2", async function () {
    const { model } = await createSpreadsheetWithList({
        columns: [
            { name: "currency_id", string: "Currency" },
            { name: "pognon", string: "Pognon" },
        ],
    });
    setCellContent(model, "A1", '=ODOO.LIST.VALUE(1, 1, "pognon")');
    setCellContent(model, "A2", '=ODOO.LIST.VALUE(1, 1, "currency_id")');
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
                    A1: '=ODOO.LIST.VALUE("1", "1", "foo")',
                },
            },
        ],
        lists: {
            1: {
                id: 1,
                columns: [
                    { name: "foo", string: "Name" },
                    { name: "contact_name", string: "Contact Name" },
                ],
                domain: [],
                model: "partner",
                orderBy: [],
                context: {},
            },
        },
    };
    const { model } = await createModelWithDataSource({ spreadsheetData });
    const ds = model.getters.getListDataSource("1");
    expect(ds.maxPosition).toBe(1);
    expect(ds.maxPositionFetched).toBe(1);
    setCellContent(model, "A1", `=ODOO.LIST.VALUE("1", "42", "foo")`);
    expect(ds.maxPosition).toBe(42);
    expect(ds.maxPositionFetched).toBe(1);
    await waitForDataLoaded(model);
    expect(ds.maxPosition).toBe(42);
    expect(ds.maxPositionFetched).toBe(42);
});

test("Spec of web_search_read is minimal", async function () {
    const spreadsheetData = {
        lists: {
            1: {
                id: 1,
                columns: [
                    { name: "currency_id", string: "Currency" },
                    { name: "pognon", string: "Pognon" },
                    { name: "foo", string: "Foo" },
                ],
                model: "partner",
                orderBy: [],
            },
        },
    };
    const { model } = await createModelWithDataSource({
        spreadsheetData,
        mockRPC: function (route, args) {
            if (args.method === "web_search_read") {
                expect(args.kwargs.specification).toEqual({
                    id: {},
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
                expect.step("web_search_read");
            }
        },
    });
    setCellContent(model, "A1", '=ODOO.LIST.VALUE(1, 1, "pognon")');
    setCellContent(model, "A2", '=ODOO.LIST.VALUE(1, 1, "currency_id")');
    setCellContent(model, "A3", '=ODOO.LIST.VALUE(1, 1, "foo")');
    await waitForDataLoaded(model);
    expect.verifySteps(["web_search_read"]);
});

test("can import (export) contextual domain", async function () {
    const uid = user.userId;
    const spreadsheetData = {
        lists: {
            1: {
                id: 1,
                columns: [
                    { name: "foo", string: "Foo" },
                    { name: "contact_name", string: "Contact Name" },
                ],
                domain: '[("foo", "=", uid)]',
                model: "partner",
                orderBy: [],
            },
        },
    };
    const { model } = await createModelWithDataSource({
        spreadsheetData,
        mockRPC: function (route, args) {
            if (args.method === "web_search_read") {
                expect(args.kwargs.domain).toEqual([["foo", "=", uid]]);
                expect.step("web_search_read");
            }
        },
    });
    setCellContent(model, "A1", '=ODOO.LIST.VALUE("1", "1", "foo")');
    await animationFrame();
    expect(model.exportData().lists[1].domain).toBe('[("foo", "=", uid)]', {
        message: "the domain is exported with the dynamic parts",
    });
    expect.verifySteps(["web_search_read"]);
});

test("can import (export) action xml id", async function () {
    const listId = 1;
    const spreadsheetData = {
        lists: {
            [listId]: {
                id: listId,
                columns: [{ name: "foo" }],
                domain: [],
                model: "partner",
                orderBy: [],
                actionXmlId: "spreadsheet.test_action",
            },
        },
    };
    const { model } = await createModelWithDataSource({ spreadsheetData });
    expect(model.getters.getListDefinition(listId).actionXmlId).toBe("spreadsheet.test_action");
    expect(model.exportData().lists[listId].actionXmlId).toBe("spreadsheet.test_action");
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

    const originalListDefinition = model.getters.getListDefinition(listId);
    const expectedDuplicatedDefinition = {
        ...originalListDefinition,
        name: `${originalListDefinition.name} (copy)`,
    };
    expect(model.getters.getListDefinition(listIds[1])).toMatchObject(expectedDuplicatedDefinition);

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

test("INSERT_ODOO_LIST_WITH_TABLE adds a table that maches the list dimension", async function () {
    const { model } = await createSpreadsheetWithList({
        linesNumber: 4,
    });
    const sheetId = model.getters.getActiveSheetId();
    const { columns: currentColumns, model: resModel } = model.getters.getListDefinition("1");
    const col = 0;
    const row = 19;
    const threshold = 5;
    const definition = generateListDefinition(resModel, currentColumns);
    const newListId = model.getters.getNextListId();
    model.dispatch("INSERT_ODOO_LIST_WITH_TABLE", {
        sheetId,
        col,
        row,
        listId: newListId,
        definition,
        linesNumber: threshold,
        mode: "static",
    });
    const table = model.getters.getTable({ sheetId, col, row });
    expect(table.range.zone).toEqual(toZone("A20:D25"));
    expect(table.type).toBe("static");
    expect(table.config).toEqual({ ...PIVOT_STATIC_TABLE_CONFIG, firstColumn: false });
});

test("An error is displayed if the list has invalid model", async function () {
    const { model } = await createSpreadsheetWithList({
        mockRPC: async function (route, { model, method, kwargs }) {
            if (model === "unknown" && method === "fields_get") {
                throw makeServerError({ code: 404 });
            }
        },
    });
    const listId = model.getters.getListIds()[0];
    const listDefinition = model.getters.getListDefinition(listId);
    model.dispatch("UPDATE_ODOO_LIST", {
        listId,
        list: {
            ...listDefinition,
            model: "unknown",
        },
    });
    setCellContent(model, "A1", `=ODOO.LIST.VALUE(1,1,"foo")`);
    await animationFrame();
    expect(getCellValue(model, "A1")).toBe("#ERROR");
    expect(getEvaluatedCell(model, "A1").message).toBe(`The model "unknown" does not exist.`);
    const listDataSource = model.getters.getListDataSource(listId);
    expect(() => listDataSource.getFields()).toThrow(spreadsheet.EvaluationError);
});

test("Support field chaining in list", async function () {
    const { model } = await createSpreadsheetWithList();
    const listId = model.getters.getListIds()[0];
    setCellContent(model, "A1", `=ODOO.LIST.VALUE(${listId}, 1, "product_id.id")`);
    await animationFrame();
    expect(getCellValue(model, "A1")).toBe(37);
});

test("Support many2many field chaining in list", async function () {
    Partner._records = [
        {
            id: 1,
            user_ids: [7, 8],
        },
    ];
    ResUsers._records = [
        { id: 7, name: "Alice", group_ids: [1, 2], partner_id: 1 },
        { id: 8, name: "Bob", group_ids: [2, 3], partner_id: 1 },
    ];
    ResGroup._records = [
        { id: 1, name: "Group 1" },
        { id: 2, name: "Group 2" },
        { id: 3, name: "Group 3" },
    ];
    const { model } = await createSpreadsheetWithList();
    const listId = model.getters.getListIds()[0];
    setCellContent(model, "A1", `=ODOO.LIST.VALUE(${listId}, 1, "user_ids.id")`);
    setCellContent(model, "A2", `=ODOO.LIST.VALUE(${listId}, 1, "user_ids.group_ids.id")`);
    await animationFrame();
    expect(getCellValue(model, "A1")).toBe("7, 8");
    expect(getCellValue(model, "A2")).toBe("1, 2, 2, 3");
});

test("Invalid field chaining in list should be marked as such", async function () {
    const { model } = await createSpreadsheetWithList();
    const listId = model.getters.getListIds()[0];
    setCellContent(model, "A1", `=ODOO.LIST.VALUE(${listId}, 1, "product_id.id.id")`);
    await animationFrame();
    expect(getCellValue(model, "A1")).toBe("#ERROR");
    expect(getEvaluatedCell(model, "A1").message).toBe(
        `The field product_id.id.id does not exist or you do not have access to that field`
    );
});

test("Field chaining can be more than 1 deep", async function () {
    const { model } = await createSpreadsheetWithList();
    const listId = model.getters.getListIds()[0];
    setCellContent(model, "A1", `=ODOO.LIST.VALUE(${listId}, 2, "product_id.template_id.name")`);
    await animationFrame();
    expect(getCellValue(model, "A1")).toBe("xphone");
});

test("Chaining fields are fetched with the same web_search_read", async function () {
    let initialLoad = true;
    const { model } = await createSpreadsheetWithList({
        mockRPC: function (route, args) {
            if (args.method === "web_search_read") {
                if (!initialLoad) {
                    expect(args.kwargs.specification).toEqual({
                        id: {},
                        bar: {},
                        date: {},
                        foo: {},
                        product_id: {
                            fields: {
                                display_name: {},
                                template_id: {
                                    fields: {
                                        name: {},
                                        display_name: {},
                                    },
                                },
                            },
                        },
                    });
                    expect.step("web_search_read");
                }
            }
        },
    });
    const listId = model.getters.getListIds()[0];
    setCellContent(model, "A1", `=ODOO.LIST.VALUE(${listId}, 1, "product_id.template_id.name")`);
    initialLoad = false;
    await animationFrame();
    expect.verifySteps(["web_search_read"]);
});

test("Chaining monetary fields includes the currency field", async function () {
    let initialLoad = true;
    const { model } = await createSpreadsheetWithList({
        mockRPC: function (route, args) {
            if (args.method === "web_search_read") {
                if (!initialLoad) {
                    expect(args.kwargs.specification).toEqual({
                        id: {},
                        bar: {},
                        date: {},
                        foo: {},
                        product_id: {
                            fields: {
                                display_name: {},
                                pognon: {},
                                currency_id: {
                                    fields: {
                                        name: {},
                                        symbol: {},
                                        decimal_places: {},
                                        position: {},
                                    },
                                },
                            },
                        },
                    });
                    expect.step("web_search_read");
                }
            }
        },
    });
    const listId = model.getters.getListIds()[0];
    setCellContent(model, "A1", `=ODOO.LIST.VALUE(${listId}, 1, "product_id.pognon")`);
    initialLoad = false;
    await animationFrame();
    expect(getCellValue(model, "A1")).toBe(699.99);
    expect(getEvaluatedCell(model, "A1").formattedValue).toBe("$699.99");
    expect.verifySteps(["web_search_read"]);
});

test("INSERT_ODOO_LIST should provide a list of columns with name and string at minimum", function () {
    const model = new Model();
    const result = model.dispatch("INSERT_ODOO_LIST", {
        listId: "1",
        sheetId: model.getters.getActiveSheetId(),
        col: 0,
        row: 0,
        definition: {
            context: {},
            domain: [],
            model: "partner",
            orderBy: [],
            columns: [{ name: "foo" }],
        },
    });
    expect(result.reasons).toEqual([CommandResult.InvalidListDefinition]);
});

test("UPDATE_ODOO_LIST should provide a list of columns with name and string at minimum", async () => {
    const { model } = await createSpreadsheetWithList();
    const listId = model.getters.getListIds()[0];
    const definition = model.getters.getListDefinition(listId);

    const result = model.dispatch("UPDATE_ODOO_LIST", {
        listId,
        list: { ...definition, columns: [{ name: "foo" }] },
    });
    expect(result.reasons).toEqual([CommandResult.InvalidListDefinition]);
});

test("UPDATE_ODOO_LIST is rejected if the definition is unchanged", async () => {
    const { model } = await createSpreadsheetWithList();
    const listId = model.getters.getListIds()[0];
    const result = model.dispatch("UPDATE_ODOO_LIST", {
        listId,
        list: model.getters.getListDefinition(listId),
    });
    expect(result.reasons).toEqual([CommandResult.ListDefinitionUnchanged]);
});

test("Dynamic Odoo list formula", async () => {
    const spreadsheetData = {
        lists: {
            1: {
                model: "partner",
                context: {},
                domain: [],
                orderBy: [],
                columns: [
                    { name: "foo", string: "Foo" },
                    { name: "bar", string: "Bar" },
                    { name: "date", string: "Date" },
                    { name: "product_id", string: "Product" },
                ],
            },
        },
        sheets: [
            {
                cells: {
                    A1: "=ODOO.LIST(1)",
                },
            },
        ],
    };

    const { model } = await createModelWithDataSource({ spreadsheetData });

    expect(getEvaluatedGrid(model, "A1:D6")).toEqual([
        ["Foo", "Bar", "Date", "Product"],
        [12, true, 42474, "xphone"],
        [1, true, 42669, "xpad"],
        [17, true, 42719, "xpad"],
        [2, false, 42715, "xpad"],
        [null, null, null, null],
    ]);
    setCellContent(model, "A1", "=ODOO.LIST(1,2)");
    expect(getEvaluatedGrid(model, "A1:D6")).toEqual([
        ["Foo", "Bar", "Date", "Product"],
        [12, true, 42474, "xphone"],
        [1, true, 42669, "xpad"],
        [null, null, null, null],
        [null, null, null, null],
        [null, null, null, null],
    ]);
    // only spread up to the number of records available
    setCellContent(model, "A1", "=ODOO.LIST(1,30)");
    expect(getEvaluatedGrid(model, "A1:D6")).toEqual([
        ["Foo", "Bar", "Date", "Product"],
        [12, true, 42474, "xphone"],
        [1, true, 42669, "xpad"],
        [17, true, 42719, "xpad"],
        [2, false, 42715, "xpad"],
        [null, null, null, null],
    ]);
});

test("Insert dynamic odoo list", async () => {
    const { model } = await createModelWithDataSource();
    model.dispatch("INSERT_ODOO_LIST", {
        listId: "1",
        sheetId: model.getters.getActiveSheetId(),
        col: 0,
        row: 0,
        definition: {
            context: {},
            domain: [],
            model: "partner",
            orderBy: [],
            columns: [{ name: "foo", string: "Foo" }],
        },
        linesNumber: 10,
        mode: "dynamic",
    });
    expect(getCellFormula(model, "A1")).toBe("=ODOO.LIST(1, 10)");
});

test("Re-insert dynamic odoo lists", async () => {
    const { model } = await createSpreadsheetWithList();
    const definition = model.getters.getListDefinition("1");
    model.dispatch("RE_INSERT_ODOO_LIST", {
        listId: "1",
        col: 20,
        row: 20,
        sheetId: model.getters.getActiveSheetId(),
        linesNumber: 5,
        columns: definition.columns,
    });

    expect(getCellFormula(model, "U21")).toBe("=ODOO.LIST(1, 5)");
});

test("fields added to the field definition are fetched directly", async () => {
    const spreadsheetData = {
        lists: {
            1: {
                model: "partner",
                context: {},
                domain: [],
                orderBy: [],
                columns: [{ name: "foo", string: "Foo" }],
            },
        },
    };
    const { model } = await createModelWithDataSource({
        spreadsheetData,
        mockRPC: function (route, args) {
            if (args.method === "web_search_read") {
                expect.step(Object.keys(args.kwargs.specification).join(","));
            }
        },
    });
    setCellContent(model, "A1", '=ODOO.LIST.VALUE(1, 1, "foo")');
    await waitForDataLoaded(model);
    const definition = model.getters.getListDefinition("1");
    expect.verifySteps(["foo,id"]);
    model.dispatch("UPDATE_ODOO_LIST", {
        listId: "1",
        list: {
            ...definition,
            columns: [
                { name: "foo", string: "Foo" },
                { name: "bar", string: "Bar" },
            ],
        },
    });
    await waitForDataLoaded(model);
    expect.verifySteps(["foo,id,bar"]);
});
