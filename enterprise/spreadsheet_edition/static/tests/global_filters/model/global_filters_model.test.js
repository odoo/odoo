import { animationFrame } from "@odoo/hoot-mock";
import { defineSpreadsheetModels } from "@spreadsheet/../tests/helpers/data";
import { describe, expect, test } from "@odoo/hoot";

import { registries } from "@odoo/o-spreadsheet";
import { getCellValue, getCell, getEvaluatedGrid } from "@spreadsheet/../tests/helpers/getters";
import {
    addGlobalFilter,
    selectCell,
    setCellContent,
} from "@spreadsheet/../tests/helpers/commands";
import { createSpreadsheetWithPivot } from "@spreadsheet/../tests/helpers/pivot";
import { waitForDataLoaded } from "@spreadsheet/helpers/model";

describe.current.tags("headless");
defineSpreadsheetModels();

const { cellMenuRegistry } = registries;

const testGlobalFilter = {
    id: "42",
    type: "relation",
    defaultValue: [41],
};
const testFieldMatching = {
    pivot: { "PIVOT#1": { chain: "product_id", type: "many2one" } },
};

test("Can set a value from a pivot header context menu", async function () {
    const { env, model } = await createSpreadsheetWithPivot({
        arch: /*xml*/ `
                <pivot>
                    <field name="product_id" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
    });
    expect(getCellValue(model, "B3")).toBe(10);
    expect(getCellValue(model, "B4")).toBe(121.0);
    await addGlobalFilter(
        model,
        {
            id: "42",
            type: "relation",
            defaultValue: [41],
        },
        {
            pivot: { "PIVOT#1": { chain: "product_id", type: "many2one" } },
        }
    );
    expect(getCellValue(model, "B3")).toBe("");
    expect(getCellValue(model, "B4")).toBe(121);
    selectCell(model, "A3");
    expect(getCell(model, "B3").content).toBe('=PIVOT.VALUE(1,"probability:avg","product_id",37)', {
        message: "the formula field matches the filter",
    });
    const root = cellMenuRegistry.getMenuItems().find((item) => item.id === "use_global_filter");
    expect(root.isVisible(env)).toBe(true);
    await root.execute(env);
    await animationFrame();
    expect(getCellValue(model, "B3")).toBe(10);
    expect(getCellValue(model, "B4")).toBe("");
    await root.execute(env);
    await animationFrame();
    expect(getCellValue(model, "B3")).toBe(10);
    expect(getCellValue(model, "B4")).toBe(121);

    model.dispatch("CREATE_SHEET", { sheetId: "42" });
    setCellContent(model, "A1", `=PIVOT("1")`, "42");
    selectCell(model, "A3", "42");
    expect(root.isVisible(env)).toBe(true);
    await root.execute(env);
    await animationFrame();
    // prettier-ignore
    expect(getEvaluatedGrid(model, "A1:B4")).toEqual([
            ["(#1) Partner Pivot",  "Total"],
            ["",                    "Probability"],
            ["xphone",              10],
            ["Total",               10],
        ])
    await root.execute(env);
    await animationFrame();
    // prettier-ignore
    expect(getEvaluatedGrid(model, "A1:B5")).toEqual([
            ["(#1) Partner Pivot",  "Total"],
            ["",                    "Probability"],
            ["xphone",              10],
            ["xpad",                121],
            ["Total",               131],
        ])
});

test("Can open context menu with positional argument", async function () {
    const { env, model } = await createSpreadsheetWithPivot({
        arch: /*xml*/ `
                <pivot>
                    <field name="product_id" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
    });
    setCellContent(model, "B3", '=PIVOT.HEADER(1, "#product_id", 1)');
    await addGlobalFilter(
        model,
        {
            id: "42",
            type: "relation",
            defaultValue: [],
        },
        { pivot: { "PIVOT#1": { chain: "product_id", type: "many2one" } } }
    );
    selectCell(model, "B3");
    const root = cellMenuRegistry.getMenuItems().find((item) => item.id === "use_global_filter");
    expect(root.isVisible(env)).toBe(true);
});

test("Can open context menu without argument", async function () {
    const { env, model } = await createSpreadsheetWithPivot({
        arch: /*xml*/ `
                <pivot>
                    <field name="product_id" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
    });
    expect(getCell(model, "B5").content).toBe('=PIVOT.VALUE(1,"probability:avg")');
    await addGlobalFilter(
        model,
        {
            id: "42",
            type: "relation",
            defaultValue: [],
        },
        { pivot: { "PIVOT#1": { chain: "product_id", type: "many2one" } } }
    );
    selectCell(model, "B5");
    const root = cellMenuRegistry.getMenuItems().find((item) => item.id === "use_global_filter");
    expect(root.isVisible(env)).toBe(false);

    model.dispatch("CREATE_SHEET", { sheetId: "42" });
    setCellContent(model, "A1", `=PIVOT("1")`, "42");
    selectCell(model, "B5", "42");
    expect(root.isVisible(env)).toBe(false);
});

test("Can open context menu when there is a filter with no field defined", async function () {
    const { env, model } = await createSpreadsheetWithPivot({
        arch: /*xml*/ `
                <pivot>
                    <field name="product_id" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
    });
    await addGlobalFilter(model, {
        id: "42",
        type: "relation",
        defaultValue: [],
    });
    selectCell(model, "B3");
    const root = cellMenuRegistry.getMenuItems().find((item) => item.id === "use_global_filter");
    expect(root.isVisible(env)).toBe(false);

    model.dispatch("CREATE_SHEET", { sheetId: "42" });
    setCellContent(model, "A1", `=PIVOT("1")`, "42");
    selectCell(model, "B3", "42");
    expect(root.isVisible(env)).toBe(false);
});

test("Set as filter is not visible if there is no pivot formula", async function () {
    const { env, model } = await createSpreadsheetWithPivot();
    selectCell(model, "A1");
    setCellContent(model, "A1", "=1");
    const root = cellMenuRegistry.getMenuItems().find((item) => item.id === "use_global_filter");
    expect(root.isVisible(env)).toBe(false);
});

test("Set as filter is not visible on empty cells of PIVOT", async function () {
    const { env, model } = await createSpreadsheetWithPivot();
    const root = cellMenuRegistry.getMenuItems().find((item) => item.id === "use_global_filter");
    model.dispatch("CREATE_SHEET", { sheetId: "42" });
    setCellContent(model, "A1", `=PIVOT("1")`, "42");
    selectCell(model, "A1", "42");
    expect(root.isVisible(env)).toBe(false);
    selectCell(model, "A2", "42");
    expect(root.isVisible(env)).toBe(false);
});

test("menu to set filter value is not visible if no filter matches", async function () {
    const { env, model } = await createSpreadsheetWithPivot();
    await addGlobalFilter(
        model,
        {
            id: "42",
            type: "relation",
            defaultValue: [41],
        },
        {
            pivot: { "PIVOT#1": { chain: "product_id", type: "many2one" } },
        }
    );
    selectCell(model, "A30");
    const root = cellMenuRegistry.getMenuItems().find((item) => item.id === "use_global_filter");
    expect(root.isVisible(env)).toBe(false);
});

test("menu to set filter value is only visible on the PIVOT.HEADER formulas", async function () {
    const { env, model } = await createSpreadsheetWithPivot({
        arch: /*xml*/ `
                    <pivot>
                        <field name="product_id" type="row"/>
                        <field name="probability" type="measure"/>
                    </pivot>`,
    });
    await addGlobalFilter(model, testGlobalFilter, testFieldMatching);
    const root = cellMenuRegistry.getMenuItems().find((item) => item.id === "use_global_filter");

    selectCell(model, "A3");
    expect(getCell(model, "A3").content.includes("PIVOT.HEADER(")).not.toBe(undefined);
    expect(root.isVisible(env)).toBe(true);

    selectCell(model, "B3");
    expect(getCell(model, "B3").content.includes("PIVOT.VALUE(")).not.toBe(undefined);
    expect(root.isVisible(env)).toBe(false);
});

test("menu to set filter value is only visible on the the header of a PIVOT.TABLE", async function () {
    const { env, model } = await createSpreadsheetWithPivot({
        arch: /*xml*/ `
                    <pivot>
                        <field name="product_id" type="row"/>
                        <field name="probability" type="measure"/>
                    </pivot>`,
    });
    await addGlobalFilter(model, testGlobalFilter, testFieldMatching);
    const sheetIdFrom = model.getters.getActiveSheetId();
    model.dispatch("CREATE_SHEET", { sheetId: "42", position: 1 });
    model.dispatch("ACTIVATE_SHEET", { sheetIdFrom, sheetIdTo: "42" });
    setCellContent(model, "A1", '=PIVOT("1")');
    const root = cellMenuRegistry.getMenuItems().find((item) => item.id === "use_global_filter");

    selectCell(model, "A3"); // Header cell
    expect(root.isVisible(env)).toBe(true);

    selectCell(model, "B3"); // Not a header cell
    expect(root.isVisible(env)).toBe(false);
});

test("UNDO/REDO filter creation with multiple field matchings", async function () {
    const { model } = await createSpreadsheetWithPivot();
    expect(getCellValue(model, "B4")).toBe(11);
    const filter = {
        id: "42",
        type: "relation",
        defaultValue: [2],
    };
    await addGlobalFilter(model, filter, {
        pivot: { "PIVOT#1": { chain: "product_id", type: "many2one" } },
    });
    model.dispatch("REQUEST_UNDO");
    expect(model.getters.getGlobalFilters().length).toBe(0);
    model.dispatch("REQUEST_REDO");
    expect(model.getters.getGlobalFilters().length).toBe(1);
});

test("UNDO/REDO filter creation reloads the related field matchings", async function () {
    const { model } = await createSpreadsheetWithPivot();
    expect(getCellValue(model, "B4")).toBe(11);
    const filter = {
        id: "42",
        type: "relation",
        defaultValue: [2],
    };
    await addGlobalFilter(model, filter, {
        pivot: { "PIVOT#1": { chain: "product_id", type: "many2one" } },
    });
    expect(getCellValue(model, "B4")).toBe("");
    model.dispatch("REQUEST_UNDO");
    expect(model.getters.getGlobalFilters().length).toBe(0);
    await waitForDataLoaded(model);
    expect(getCellValue(model, "B4")).toBe(11);
    model.dispatch("REQUEST_REDO");
    expect(model.getters.getGlobalFilters().length).toBe(1);
    await waitForDataLoaded(model);
    expect(getCellValue(model, "B4")).toBe("");
});
