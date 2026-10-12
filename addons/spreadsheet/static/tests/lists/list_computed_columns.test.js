import { describe, expect, test } from "@odoo/hoot";
import { setCellContent, redo, undo } from "@spreadsheet/../tests/helpers/commands";
import { getCellValue, getEvaluatedCell } from "@spreadsheet/../tests/helpers/getters";
import { createSpreadsheetWithList } from "@spreadsheet/../tests/helpers/list";
import { createModelWithDataSource } from "@spreadsheet/../tests/helpers/model";
import {
    defineSpreadsheetActions,
    defineSpreadsheetModels,
} from "@spreadsheet/../tests/helpers/data";
import { waitForDataLoaded } from "@spreadsheet/helpers/model";

describe.current.tags("headless");
defineSpreadsheetModels();
defineSpreadsheetActions();

test("computed column with a constant formula", async () => {
    const { model } = await createSpreadsheetWithList({
        columns: [{ name: "foo", string: "Foo" }],
        linesNumber: 4,
    });
    const [listId] = model.getters.getListIds();
    const sheetId = model.getters.getActiveSheetId();
    const listDef = model.getters.getListDefinition(listId);
    model.dispatch("UPDATE_ODOO_LIST", {
        listId,
        list: {
            ...listDef,
            columns: [
                ...listDef.columns,
                {
                    name: "computed",
                    string: "Computed",
                    computedBy: { formula: "=42", sheetId },
                },
            ],
        },
    });
    await waitForDataLoaded(model);

    setCellContent(model, "A1", '=ODOO.LIST.VALUE(1, 1, "computed")');
    setCellContent(model, "A2", '=ODOO.LIST.VALUE(1, 2, "computed")');
    setCellContent(model, "A3", '=ODOO.LIST.VALUE(1, 3, "computed")');
    setCellContent(model, "A4", '=ODOO.LIST.VALUE(1, 4, "computed")');
    await waitForDataLoaded(model);
    expect(getCellValue(model, "A1")).toBe(42);
    expect(getCellValue(model, "A2")).toBe(42);
    expect(getCellValue(model, "A3")).toBe(42);
    expect(getCellValue(model, "A4")).toBe(42);
});

test("computed column referencing another column by its string name", async () => {
    // Partner.foo values: [12, 1, 17, 2]
    // Formula: =foo*2  →  [24, 2, 34, 4]
    const { model } = await createSpreadsheetWithList({
        columns: [
            { name: "foo", string: "Foo" },
            { name: "bar", string: "Bar" },
        ],
        linesNumber: 4,
    });
    const [listId] = model.getters.getListIds();
    const sheetId = model.getters.getActiveSheetId();
    const listDef = model.getters.getListDefinition(listId);
    model.dispatch("UPDATE_ODOO_LIST", {
        listId,
        list: {
            ...listDef,
            columns: [
                ...listDef.columns,
                {
                    name: "'2 Foo'",
                    string: "2 Foo",
                    computedBy: { formula: "=foo*2", sheetId },
                },
            ],
        },
    });
    await waitForDataLoaded(model);

    setCellContent(model, "A1", "=ODOO.LIST.VALUE(1, 1, \"'2 Foo'\")");
    setCellContent(model, "A2", "=ODOO.LIST.VALUE(1, 2, \"'2 Foo'\")");
    setCellContent(model, "A3", "=ODOO.LIST.VALUE(1, 3, \"'2 Foo'\")");
    setCellContent(model, "A4", "=ODOO.LIST.VALUE(1, 4, \"'2 Foo'\")");
    await waitForDataLoaded(model);
    expect(getCellValue(model, "A1")).toBe(24); // 12 * 2
    expect(getCellValue(model, "A2")).toBe(2); // 1 * 2
    expect(getCellValue(model, "A3")).toBe(34); // 17 * 2
    expect(getCellValue(model, "A4")).toBe(4); // 2 * 2
});

test("computed column referencing a spreadsheet cell", async () => {
    const { model } = await createSpreadsheetWithList({
        columns: [{ name: "foo", string: "Foo" }],
        linesNumber: 4,
    });
    const [listId] = model.getters.getListIds();
    const sheetId = model.getters.getActiveSheetId();
    const listDef = model.getters.getListDefinition(listId);

    // Put the multiplier in a cell
    setCellContent(model, "A20", "3");

    model.dispatch("UPDATE_ODOO_LIST", {
        listId,
        list: {
            ...listDef,
            columns: [
                ...listDef.columns,
                {
                    name: "computed",
                    string: "Computed",
                    computedBy: { formula: "=foo*A20", sheetId },
                },
            ],
        },
    });
    await waitForDataLoaded(model);

    setCellContent(model, "A1", '=ODOO.LIST.VALUE(1, 1, "computed")');
    await waitForDataLoaded(model);
    expect(getCellValue(model, "A1")).toBe(36); // 12 * 3
});

test("computed column is recomputed when its cell dependency changes", async () => {
    const { model } = await createSpreadsheetWithList({
        columns: [{ name: "foo", string: "Foo" }],
        linesNumber: 4,
    });
    const [listId] = model.getters.getListIds();
    const sheetId = model.getters.getActiveSheetId();
    const listDef = model.getters.getListDefinition(listId);

    setCellContent(model, "A20", "2");

    model.dispatch("UPDATE_ODOO_LIST", {
        listId,
        list: {
            ...listDef,
            columns: [
                ...listDef.columns,
                {
                    name: "computed",
                    string: "Computed",
                    computedBy: { formula: "=foo*A20", sheetId },
                },
            ],
        },
    });
    await waitForDataLoaded(model);

    setCellContent(model, "A1", '=ODOO.LIST.VALUE(1, 1, "computed")');
    await waitForDataLoaded(model);
    expect(getCellValue(model, "A1")).toBe(24); // 12 * 2

    setCellContent(model, "A20", "5");
    expect(getCellValue(model, "A1")).toBe(60); // 12 * 5
});

test("chained computed columns", async () => {
    // Computed1 = Foo * 3, Computed2 = Computed1 * 2
    // For foo=12: Computed1=36, Computed2=72
    const { model } = await createSpreadsheetWithList({
        columns: [{ name: "foo", string: "Foo" }],
        linesNumber: 4,
    });
    const [listId] = model.getters.getListIds();
    const sheetId = model.getters.getActiveSheetId();
    const listDef = model.getters.getListDefinition(listId);
    model.dispatch("UPDATE_ODOO_LIST", {
        listId,
        list: {
            ...listDef,
            columns: [
                ...listDef.columns,
                {
                    name: "computed1",
                    string: "Computed1",
                    computedBy: { formula: "=foo*3", sheetId },
                },
                {
                    name: "computed2",
                    string: "Computed2",
                    computedBy: { formula: "=computed1*2", sheetId },
                },
            ],
        },
    });
    await waitForDataLoaded(model);

    setCellContent(model, "A1", '=ODOO.LIST.VALUE(1, 1, "computed1")');
    setCellContent(model, "A2", '=ODOO.LIST.VALUE(1, 1, "computed2")');
    await waitForDataLoaded(model);
    expect(getCellValue(model, "A1")).toBe(36); // 12 * 3
    expect(getCellValue(model, "A2")).toBe(72); // 12 * 3 * 2
});

test("self-referencing computed column returns #CYCLE", async () => {
    const { model } = await createSpreadsheetWithList({
        columns: [{ name: "foo", string: "Foo" }],
        linesNumber: 1,
    });
    const [listId] = model.getters.getListIds();
    const sheetId = model.getters.getActiveSheetId();
    const listDef = model.getters.getListDefinition(listId);
    model.dispatch("UPDATE_ODOO_LIST", {
        listId,
        list: {
            ...listDef,
            columns: [
                ...listDef.columns,
                {
                    name: "self",
                    string: "Self",
                    computedBy: { formula: "=self+1", sheetId },
                },
            ],
        },
    });
    await waitForDataLoaded(model);

    setCellContent(model, "A1", '=ODOO.LIST.VALUE(1, 1, "self")');
    await waitForDataLoaded(model);
    expect(getEvaluatedCell(model, "A1").value).toBe("#CYCLE");
});

test("computed column with non-existing symbol returns #N/A", async () => {
    const { model } = await createSpreadsheetWithList({
        columns: [{ name: "foo", string: "Foo" }],
        linesNumber: 1,
    });
    const [listId] = model.getters.getListIds();
    const sheetId = model.getters.getActiveSheetId();
    const listDef = model.getters.getListDefinition(listId);
    model.dispatch("UPDATE_ODOO_LIST", {
        listId,
        list: {
            ...listDef,
            columns: [
                ...listDef.columns,
                {
                    name: "Computed",
                    string: "Computed",
                    computedBy: { formula: "=NonExistingColumn*2", sheetId },
                },
            ],
        },
    });
    await waitForDataLoaded(model);

    setCellContent(model, "A1", '=ODOO.LIST.VALUE(1, 1, "Computed")');
    await waitForDataLoaded(model);
    expect(getEvaluatedCell(model, "A1").value).toBe("#N/A");
});

test("computed column works in dynamic ODOO.LIST mode", async () => {
    // Partner.foo values: [12, 1, 17, 2]
    const { model } = await createSpreadsheetWithList({
        columns: [{ name: "foo", string: "Foo" }],
        linesNumber: 4,
    });
    const [listId] = model.getters.getListIds();
    const sheetId = model.getters.getActiveSheetId();
    const listDef = model.getters.getListDefinition(listId);
    model.dispatch("UPDATE_ODOO_LIST", {
        listId,
        list: {
            ...listDef,
            columns: [
                ...listDef.columns,
                {
                    name: "Double Foo",
                    string: "Double Foo",
                    computedBy: { formula: "=foo*2", sheetId },
                },
            ],
        },
    });
    await waitForDataLoaded(model);

    // Insert the dynamic list in a separate area to check spilled values
    setCellContent(model, "P1", "=ODOO.LIST(1, 4)");
    await waitForDataLoaded(model);

    // Column 1 = Foo header/values, Column 2 = Double Foo header/values
    expect(getCellValue(model, "P1")).toBe("Foo");
    expect(getCellValue(model, "Q1")).toBe("Double Foo");
    expect(getCellValue(model, "P2")).toBe(12);
    expect(getCellValue(model, "Q2")).toBe(24); // 12 * 2
    expect(getCellValue(model, "P3")).toBe(1);
    expect(getCellValue(model, "Q3")).toBe(2); // 1 * 2
});

test("adding or updating a computed column via UPDATE_ODOO_LIST does not trigger RPC", async () => {
    let loaded = false;
    const { model } = await createSpreadsheetWithList({
        columns: [{ name: "foo", string: "Foo" }],
        mockRPC: async function (route, args) {
            if (loaded && args.method === "web_search_read" && args.model === "partner") {
                expect.step("web_search_read");
            }
        },
    });
    const [listId] = model.getters.getListIds();
    const sheetId = model.getters.getActiveSheetId();
    const listDef = model.getters.getListDefinition(listId);
    loaded = true;

    model.dispatch("UPDATE_ODOO_LIST", {
        listId,
        list: {
            ...listDef,
            columns: [
                ...listDef.columns,
                {
                    name: "computed",
                    string: "Computed",
                    computedBy: { formula: "=foo*2", sheetId },
                },
            ],
        },
    });
    await waitForDataLoaded(model);
    expect.verifySteps([]);

    model.dispatch("UPDATE_ODOO_LIST", {
        listId,
        list: {
            ...listDef,
            columns: [
                ...listDef.columns,
                {
                    name: "computed",
                    string: "Computed",
                    computedBy: { formula: "=foo*5", sheetId },
                },
            ],
        },
    });
    await waitForDataLoaded(model);
    expect.verifySteps([]);
});

test("computed column definition is preserved in export/import roundtrip", async () => {
    const { model } = await createSpreadsheetWithList({
        columns: [{ name: "foo", string: "Foo" }],
        linesNumber: 2,
    });
    const [listId] = model.getters.getListIds();
    const sheetId = model.getters.getActiveSheetId();
    const listDef = model.getters.getListDefinition(listId);
    const computedCol = {
        name: "double_foo",
        string: "Double Foo",
        computedBy: { formula: "=foo*2", sheetId },
    };
    model.dispatch("UPDATE_ODOO_LIST", {
        listId,
        list: { ...listDef, columns: [...listDef.columns, computedCol] },
    });

    const exported = model.exportData();
    const importedComputedCol = exported.lists[listId].columns.find(
        (col) => col.name === "double_foo"
    );
    expect(importedComputedCol).toMatchObject({
        name: "double_foo",
        string: "Double Foo",
        computedBy: { formula: "=foo*2", sheetId },
    });

    // Re-import and verify the value still computes correctly
    const { model: model2 } = await createModelWithDataSource({
        spreadsheetData: exported,
    });
    await waitForDataLoaded(model2);
    setCellContent(model2, "A1", '=ODOO.LIST.VALUE(1, 1, "double_foo")');
    await waitForDataLoaded(model2);
    expect(getCellValue(model2, "A1")).toBe(24); // 12 * 2
});

test("undo/redo adding a computed column", async () => {
    const { model } = await createSpreadsheetWithList({
        columns: [{ name: "foo", string: "Foo" }],
        linesNumber: 2,
    });
    const [listId] = model.getters.getListIds();
    const sheetId = model.getters.getActiveSheetId();
    const listDef = model.getters.getListDefinition(listId);

    model.dispatch("UPDATE_ODOO_LIST", {
        listId,
        list: {
            ...listDef,
            columns: [
                ...listDef.columns,
                {
                    name: "computed",
                    string: "Computed",
                    computedBy: { formula: "=foo*2", sheetId },
                },
            ],
        },
    });
    await waitForDataLoaded(model);

    expect(
        model.getters.getListDefinition(listId).columns.find((col) => col.name === "computed")
    ).toMatchObject({ name: "computed", computedBy: { formula: "=foo*2", sheetId } });

    undo(model);
    await waitForDataLoaded(model);
    expect(
        model.getters.getListDefinition(listId).columns.find((col) => col.name === "computed")
    ).toBe(undefined);

    redo(model);
    await waitForDataLoaded(model);
    expect(
        model.getters.getListDefinition(listId).columns.find((col) => col.name === "computed")
    ).toMatchObject({ name: "computed", computedBy: { formula: "=foo*2", sheetId } });
});

test("hidden column referenced by a computed column is still fetched", async () => {
    // The "Bar" column is hidden but referenced in the computed column formula.
    // It should still be fetched from the server.
    let fetchedFields = {};
    const { model } = await createSpreadsheetWithList({
        columns: [
            { name: "foo", string: "Foo" },
            { name: "probability", string: "Probability" },
        ],
        linesNumber: 4,
        mockRPC: async function (route, args) {
            if (args.method === "web_search_read" && args.model === "partner") {
                fetchedFields = args.kwargs.specification || {};
            }
        },
    });
    const [listId] = model.getters.getListIds();
    const sheetId = model.getters.getActiveSheetId();
    const listDef = model.getters.getListDefinition(listId);

    model.dispatch("UPDATE_ODOO_LIST", {
        listId,
        list: {
            ...listDef,
            columns: [
                { name: "foo", string: "Foo", hidden: true },
                { name: "probability", string: "Probability" },
                {
                    name: "computed",
                    string: "Computed",
                    computedBy: { formula: "=foo*2", sheetId },
                },
            ],
        },
    });

    model.dispatch("REFRESH_ALL_DATA_SOURCES");
    await waitForDataLoaded(model);

    expect(fetchedFields).toInclude("foo");
});

test("computed column referencing multiple other columns", async () => {
    // Probability values: [10, 11, 95, 15]. Foo values: [12, 1, 17, 2]
    // Formula: =Foo + Probability
    const { model } = await createSpreadsheetWithList({
        columns: [
            { name: "foo", string: "Foo" },
            { name: "probability", string: "Probability" },
        ],
        linesNumber: 4,
    });
    const [listId] = model.getters.getListIds();
    const sheetId = model.getters.getActiveSheetId();
    const listDef = model.getters.getListDefinition(listId);
    model.dispatch("UPDATE_ODOO_LIST", {
        listId,
        list: {
            ...listDef,
            columns: [
                ...listDef.columns,
                {
                    name: "sum_col",
                    string: "Sum",
                    computedBy: { formula: "=foo+probability", sheetId },
                },
            ],
        },
    });
    await waitForDataLoaded(model);

    setCellContent(model, "A1", '=ODOO.LIST.VALUE(1, 1, "sum_col")');
    setCellContent(model, "A2", '=ODOO.LIST.VALUE(1, 2, "sum_col")');
    setCellContent(model, "A3", '=ODOO.LIST.VALUE(1, 3, "sum_col")');
    setCellContent(model, "A4", '=ODOO.LIST.VALUE(1, 4, "sum_col")');
    await waitForDataLoaded(model);
    expect(getCellValue(model, "A1")).toBe(22); // 12 + 10
    expect(getCellValue(model, "A2")).toBe(12); // 1 + 11
    expect(getCellValue(model, "A3")).toBe(112); // 17 + 95
    expect(getCellValue(model, "A4")).toBe(17); // 2 + 15
});

test("getListCompiledColumnFormula returns the compiled formula for a computed column", async () => {
    const { model } = await createSpreadsheetWithList({
        columns: [{ name: "foo", string: "Foo" }],
        linesNumber: 1,
    });
    const [listId] = model.getters.getListIds();
    const sheetId = model.getters.getActiveSheetId();
    const listDef = model.getters.getListDefinition(listId);
    model.dispatch("UPDATE_ODOO_LIST", {
        listId,
        list: {
            ...listDef,
            columns: [
                ...listDef.columns,
                {
                    name: "computed",
                    string: "Computed",
                    computedBy: { formula: "=foo*2", sheetId },
                },
            ],
        },
    });

    const compiledFormula = model.getters.getListCompiledColumnFormula(listId, "computed");
    expect(compiledFormula).not.toBe(undefined);
});

test("getListCompiledColumnFormula returns undefined for non-computed column", async () => {
    const { model } = await createSpreadsheetWithList({
        columns: [{ name: "foo", string: "Foo" }],
        linesNumber: 1,
    });
    const [listId] = model.getters.getListIds();
    const compiledFormula = model.getters.getListCompiledColumnFormula(listId, "foo");
    expect(compiledFormula).toBe(undefined);
});

test("computed column header is its string name", async () => {
    const { model } = await createSpreadsheetWithList({
        columns: [{ name: "foo", string: "Foo" }],
        linesNumber: 1,
    });
    const [listId] = model.getters.getListIds();
    const sheetId = model.getters.getActiveSheetId();
    const listDef = model.getters.getListDefinition(listId);
    model.dispatch("UPDATE_ODOO_LIST", {
        listId,
        list: {
            ...listDef,
            columns: [
                ...listDef.columns,
                {
                    name: "computed",
                    string: "My Computed Column",
                    computedBy: { formula: "=foo*2", sheetId },
                },
            ],
        },
    });
    await waitForDataLoaded(model);

    setCellContent(model, "A1", '=ODOO.LIST.HEADER(1, "computed")');
    expect(getCellValue(model, "A1")).toBe("My Computed Column");
});
