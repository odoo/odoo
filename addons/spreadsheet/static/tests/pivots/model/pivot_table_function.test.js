import { animationFrame } from "@odoo/hoot-mock";
import { describe, expect, test, beforeEach } from "@odoo/hoot";
import {
    defineSpreadsheetActions,
    defineSpreadsheetModels,
} from "@spreadsheet/../tests/helpers/data";

import { setCellContent, updatePivot } from "@spreadsheet/../tests/helpers/commands";
import {
    getEvaluatedCell,
    getEvaluatedFormatGrid,
    getEvaluatedGrid,
} from "@spreadsheet/../tests/helpers/getters";
import { createSpreadsheetWithPivot } from "@spreadsheet/../tests/helpers/pivot";

let model;

describe.current.tags("headless");
defineSpreadsheetModels();
defineSpreadsheetActions();

beforeEach(async () => {
    ({ model } = await createSpreadsheetWithPivot({
        arch: /* xml */ `
            <pivot>
                <field name="product_id" type="col"/>
                <field name="foo" type="row"/>
                <field name="probability" type="measure"/>
            </pivot>`,
    }));
    model.dispatch("CREATE_SHEET", { sheetId: "42" });
});

test("full PIVOT() values", async function () {
    setCellContent(model, "A1", `=PIVOT("1")`, "42");
    // prettier-ignore
    expect(getEvaluatedGrid(model, "A1:D7", "42")).toEqual([
        ["(#1) Partner Pivot",    "xphone",       "xpad",         "Total"],
        ["",            "Probability",  "Probability",  "Probability"],
        [1,             "",             11,             11],
        [2,             "",             15,             15],
        [12,            10,             "",             10],
        [17,            "",             95,             95],
        ["Total",       10,             121,            131],
    ]);
});

test("full PIVOT() formats", async function () {
    setCellContent(model, "A1", `=PIVOT("1")`, "42");
    // prettier-ignore
    expect(getEvaluatedFormatGrid(model, "A1:D7", "42")).toEqual([
        [undefined, "@* ",      "@* ",      undefined],
        [undefined, undefined,  undefined,  undefined],
        ["0* ",     "#,##0.00", "#,##0.00", "#,##0.00"],
        ["0* ",     "#,##0.00", "#,##0.00", "#,##0.00"],
        ["0* ",     "#,##0.00", "#,##0.00", "#,##0.00"],
        ["0* ",     "#,##0.00", "#,##0.00", "#,##0.00"],
        [undefined, "#,##0.00", "#,##0.00", "#,##0.00"],
    ]);
});

test("PIVOT(row_count=1)", async function () {
    setCellContent(model, "A1", `=PIVOT("1", 1)`, "42");
    // prettier-ignore
    expect(getEvaluatedGrid(model, "A1:D4", "42")).toEqual([
        ["(#1) Partner Pivot",  "xphone",       "xpad",         "Total"],
        ["",                    "Probability",  "Probability",  "Probability"],
        [1,                     "",             11,             11],
        [null,                  null,           null,           null],
    ]);
});

test("PIVOT(row_count=0)", async function () {
    setCellContent(model, "A1", `=PIVOT("1", 0)`, "42");
    // prettier-ignore
    expect(getEvaluatedGrid(model, "A1:D3", "42")).toEqual([
        ["(#1) Partner Pivot",  "xphone",       "xpad",         "Total"],
        ["",                    "Probability",  "Probability",  "Probability"],
        [null,                  null,           null,           null],
    ]);
});

test("PIVOT(negative row_count)", async function () {
    setCellContent(model, "A1", `=PIVOT("1", -1)`, "42");
    expect(getEvaluatedCell(model, "A1", "42").value).toBe("#ERROR");
    expect(getEvaluatedCell(model, "A1", "42").message).toBe(
        "The number of rows must be positive."
    );
});

test("PIVOT(include_column_titles=FALSE)", async function () {
    setCellContent(model, "A1", `=PIVOT("1",,,FALSE)`, "42");
    // prettier-ignore
    expect(getEvaluatedGrid(model, "A1:D5", "42")).toEqual([
        [1,         "",             11,             11],
        [2,         "",             15,             15],
        [12,        10,             "",             10],
        [17,        "",             95,             95],
        ["Total",   10,             121,            131],
    ]);
});

test("PIVOT(include_total=FALSE) with no groupbys applied", async function () {
    const { model } = await createSpreadsheetWithPivot({
        arch: /* xml */ `
        <pivot>
            <field name="probability" type="measure"/>
        </pivot>`,
    });
    model.dispatch("CREATE_SHEET", { sheetId: "42" });
    setCellContent(model, "A1", `=PIVOT("1",,FALSE)`, "42");
    // prettier-ignore
    expect(getEvaluatedGrid(model, "A1:B3", "42")).toEqual([
            ["(#1) Partner Pivot",  "Total"],
            ["",                    "Probability"],
            ["Total",               131],
        ]);
});

test("PIVOT(include_total=FALSE) with multiple measures and no groupbys applied", async function () {
    const { model } = await createSpreadsheetWithPivot({
        arch: /* xml */ `
        <pivot>
            <field name="probability" type="measure"/>
            <field name="foo" type="measure"/>
        </pivot>`,
    });
    model.dispatch("CREATE_SHEET", { sheetId: "42" });
    setCellContent(model, "A1", `=PIVOT("1",,FALSE)`, "42");
    // prettier-ignore
    expect(getEvaluatedGrid(model, "A1:C3", "42")).toEqual([
            ["(#1) Partner Pivot",  "Total",        ""],
            ["",                    "Probability",  "Foo"],
            ["Total",               131,            32],
        ]);
});

test("PIVOT(include_total=FALSE) with only row groupby applied", async function () {
    const { model } = await createSpreadsheetWithPivot({
        arch: /* xml */ `
        <pivot>
                <field name="foo" type="row"/>
                <field name="probability" type="measure"/>
            </pivot>`,
    });
    model.dispatch("CREATE_SHEET", { sheetId: "42" });
    setCellContent(model, "A1", `=PIVOT("1",,FALSE)`, "42");
    // prettier-ignore
    expect(getEvaluatedGrid(model, "A1:C7", "42")).toEqual([
            ["(#1) Partner Pivot",  "Total",        null],
            ["",                    "Probability",  null],
            [1,                     11,             null],
            [2,                     15,             null],
            [12,                    10,             null],
            [17,                    95,             null],
            [null,                  null,           null],
        ]);
});

test("PIVOT(include_total=FALSE) with multiple measures and only row groupby applied", async function () {
    const { model } = await createSpreadsheetWithPivot({
        arch: /* xml */ `
        <pivot>
                <field name="product_id" type="row"/>
                <field name="probability" type="measure"/>
                <field name="foo" type="measure"/>
            </pivot>`,
    });
    model.dispatch("CREATE_SHEET", { sheetId: "42" });
    setCellContent(model, "A1", `=PIVOT("1",,FALSE)`, "42");
    // prettier-ignore
    expect(getEvaluatedGrid(model, "A1:D5", "42")).toEqual([
            ["(#1) Partner Pivot",      "Total",            "",        null],
            ["",                        "Probability",      "Foo",     null],
            ["xphone",                  10,                 12,        null],
            ["xpad",                    121,                20,        null],
            [null,                      null,               null,      null],
        ]);
});

test("PIVOT(include_total=FALSE) with only col groupby applied", async function () {
    const { model } = await createSpreadsheetWithPivot({
        arch: /* xml */ `
        <pivot>
            <field name="product_id" type="col"/>
            <field name="probability" type="measure"/>
        </pivot>`,
    });
    model.dispatch("CREATE_SHEET", { sheetId: "42" });
    setCellContent(model, "A1", `=PIVOT("1",,FALSE)`, "42");
    // prettier-ignore
    expect(getEvaluatedGrid(model, "A1:D4", "42")).toEqual([
            ["(#1) Partner Pivot",     "xphone",          "xpad",            null],
            ["",                       "Probability",     "Probability",     null],
            ["Total",                  10,                121,               null],
            [null,                     null,              null,              null],
        ]);
});

test("PIVOT(include_total=FALSE, include_column_titles=FALSE)", async function () {
    setCellContent(model, "A1", `=PIVOT("1",,FALSE,FALSE)`, "42");
    // prettier-ignore
    expect(getEvaluatedGrid(model, "A1:D5", "42")).toEqual([
            [1,         "",             11,             null],
            [2,         "",             15,             null],
            [12,        10,             "",             null],
            [17,        "",             95,             null],
            [null,      null,           null,           null],
        ]);
});

test("PIVOT(row_count=1, include_total=FALSE, include_column_titles=FALSE)", async function () {
    setCellContent(model, "A1", `=PIVOT("1",1,FALSE,FALSE)`, "42");
    // prettier-ignore
    expect(getEvaluatedGrid(model, "A1:D2", "42")).toEqual([
            [1,         "",             11,             null],
            [null,      null,           null,           null],
        ]);
});

test("PIVOT(row_count=0, include_total=FALSE, include_column_titles=FALSE)", async function () {
    setCellContent(model, "A1", `=PIVOT("1",0,FALSE,FALSE)`, "42");
    // prettier-ignore
    expect(getEvaluatedGrid(model, "A1:D1", "42")).toEqual([
            ["(#1) Partner Pivot", null, null, null],
        ]);
});

test("PIVOT(row_count=0, include_total=TRUE, include_column_titles=FALSE)", async function () {
    setCellContent(model, "A1", `=PIVOT("1",0,TRUE,FALSE)`, "42");
    // prettier-ignore
    expect(getEvaluatedGrid(model, "A1:D1", "42")).toEqual([
            ["(#1) Partner Pivot", null, null, null],
        ]);
});

test("PIVOT with multiple row groups", async function () {
    const { model } = await createSpreadsheetWithPivot({
        arch: /* xml */ `
            <pivot>
                <field name="product_id" type="col"/>
                <field name="foo" type="row"/>
                <field name="id" type="row"/>
                <field name="probability" type="measure"/>
            </pivot>`,
    });
    const firstSheetId = model.getters.getActiveSheetId();
    // values in the first sheet from the individual pivot functions
    // prettier-ignore
    expect(getEvaluatedGrid(model, "A1:D11", firstSheetId)).toEqual([
        [null,          "xphone",       "xpad",         "Total"],
        [null,         "Probability",  "Probability",  "Probability"],
        [1,             "",             11,             11],
        [2,             "",             11,             11],
        [2,             "",             15,             15],
        [4,             "",             15,             15],
        [12,            10,             "",             10],
        [1,             10,             "",             10],
        [17,            "",             95,             95],
        [3,             "",             95,             95],
        ["Total",       10,             121,              131],
    ]);
    model.dispatch("CREATE_SHEET", { sheetId: "42" });
    setCellContent(model, "A1", `=PIVOT("1")`, "42");
    // values from the PIVOT function
    // prettier-ignore
    expect(getEvaluatedGrid(model, "A1:D11", "42")).toEqual([
        ["(#1) Partner Pivot",  "xphone",       "xpad",         "Total"],
        ["",                    "Probability",  "Probability",  "Probability"],
        [1,                     "",             11,             11],
        [2,                     "",             11,             11],
        [2,                     "",             15,             15],
        [4,                     "",             15,             15],
        [12,                    10,             "",             10],
        [1,                     10,             "",             10],
        [17,                    "",             95,             95],
        [3,                     "",             95,             95],
        ["Total",               10,             121,              131],
    ]);
    setCellContent(model, "A1", `=PIVOT("1",,FALSE)`, "42");
    // values from the PIVOT function without any group totals
    // prettier-ignore
    expect(getEvaluatedGrid(model, "A1:D11", "42")).toEqual([
        ["(#1) Partner Pivot", "xphone",       "xpad",         null],
        ["",                   "Probability",  "Probability",  null],
        [1,                    "",             "",             null], // group header but without total values
        [2,                    "",             11,             null],
        [2,                    "",             "",             null], // group header but without total values
        [4,                    "",             15,             null],
        [12,                   "",             "",             null], // group header but without total values
        [1,                    10,             "",             null],
        [17,                   "",             "",             null], // group header but without total values
        [3,                    "",             95,             null],
        [null,                 null,           null,           null],
    ]);
});

test("edit pivot groups", async function () {
    setCellContent(model, "A1", `=PIVOT("1")`, "42");
    const originalGrid = getEvaluatedGrid(model, "A1:D7", "42");
    // prettier-ignore
    expect(originalGrid).toEqual([
        ["(#1) Partner Pivot",    "xphone",       "xpad",         "Total"],
        ["",            "Probability",  "Probability",  "Probability"],
        [1,             "",             11,             11],
        [2,             "",             15,             15],
        [12,            10,             "",             10],
        [17,            "",             95,             95],
        ["Total",       10,             121,            131],
    ]);
    const [pivotId] = model.getters.getPivotIds();
    model.dispatch("UPDATE_PIVOT", {
        pivotId,
        pivot: {
            ...model.getters.getPivotCoreDefinition(pivotId),
            columns: [],
            rows: [],
        },
    });
    await animationFrame();
    // prettier-ignore
    expect(getEvaluatedGrid(model, "A1:B3", "42")).toEqual([
        ["(#1) Partner Pivot",  "Total"],
        ["",                    "Probability"],
        ["Total",               131],
    ]);
    model.dispatch("REQUEST_UNDO");
    await animationFrame();
    expect(getEvaluatedGrid(model, "A1:D7", "42")).toEqual(originalGrid);
});

test("Renaming the pivot reevaluates the PIVOT function", async function () {
    const pivotId = model.getters.getPivotIds()[0];
    setCellContent(model, "A1", `=PIVOT("1")`, "42");
    expect(getEvaluatedCell(model, "A1", "42").value).toBe("(#1) Partner Pivot");
    model.dispatch("RENAME_PIVOT", {
        pivotId,
        name: "New Name",
    });
    expect(getEvaluatedCell(model, "A1", "42").value).toBe("(#1) New Name");
});

test("can hide a measure", async function () {
    const { model } = await createSpreadsheetWithPivot({
        arch: /* xml */ `
        <pivot>
            <field name="probability" type="measure"/>
            <field name="foo" type="measure"/>
        </pivot>`,
    });
    setCellContent(model, "A10", '=PIVOT("1")');
    // prettier-ignore
    expect(getEvaluatedGrid(model, "A10:C12")).toEqual([
        ["(#1) Partner Pivot",      "Total",            "",],
        ["",                        "Probability",      "Foo"],
        ["Total",                   131,                32],
    ]);
    const [pivotId] = model.getters.getPivotIds();
    const definition = model.getters.getPivotCoreDefinition(pivotId);
    updatePivot(model, pivotId, {
        measures: [{ ...definition.measures[0], isHidden: true }, definition.measures[1]],
    });
    await animationFrame();
    // prettier-ignore
    expect(getEvaluatedGrid(model, "A10:C12")).toEqual([
        ["(#1) Partner Pivot",      "Total",    null],
        ["",                        "Foo",      null],
        ["Total",                   32,         null],
    ]);
});
