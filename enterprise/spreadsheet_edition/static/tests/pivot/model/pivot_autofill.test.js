import { defineSpreadsheetModels } from "@spreadsheet/../tests/helpers/data";
import { describe, expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import * as spreadsheet from "@odoo/o-spreadsheet";
const { toCartesian, toZone } = spreadsheet.helpers;
import {
    autofill,
    selectCell,
    setCellContent,
    setCellFormat,
    setCellStyle,
    updatePivot,
} from "@spreadsheet/../tests/helpers/commands";
import { getCellFormula, getCell } from "@spreadsheet/../tests/helpers/getters";
import { createSpreadsheetWithPivot } from "@spreadsheet/../tests/helpers/pivot";
import { createModelFromGrid } from "@spreadsheet/../tests/helpers/model";
import { patchTranslations } from "@web/../tests/web_test_helpers";

describe.current.tags("headless");
defineSpreadsheetModels();

/**
 * Get the computed value that would be autofilled starting from the given xc.
 * The starting xc should contains a Pivot formula
 */
function getPivotAutofillValue(model, xc, { direction, steps }) {
    const content = getCellFormula(model, xc);
    const column = ["left", "right"].includes(direction);
    const increment = ["left", "top"].includes(direction) ? -steps : steps;
    return model.getters.getPivotNextAutofillValue(content, column, increment);
}

test("Autofill pivot values", async function () {
    const { model } = await createSpreadsheetWithPivot();

    // From value to value
    expect(getPivotAutofillValue(model, "C3", { direction: "bottom", steps: 1 })).toBe(
        getCellFormula(model, "C4")
    );
    expect(getPivotAutofillValue(model, "B4", { direction: "top", steps: 1 })).toBe(
        getCellFormula(model, "B3")
    );
    expect(getPivotAutofillValue(model, "C3", { direction: "right", steps: 1 })).toBe(
        getCellFormula(model, "D3")
    );
    expect(getPivotAutofillValue(model, "C3", { direction: "left", steps: 1 })).toBe(
        getCellFormula(model, "B3")
    );
    expect(getPivotAutofillValue(model, "C3", { direction: "bottom", steps: 2 })).toBe(
        getCellFormula(model, "C5")
    );
    expect(getPivotAutofillValue(model, "C3", { direction: "bottom", steps: 3 })).toBe("");
    expect(getPivotAutofillValue(model, "C3", { direction: "right", steps: 4 })).toBe("");
    // From value to header
    expect(getPivotAutofillValue(model, "B4", { direction: "left", steps: 1 })).toBe(
        getCellFormula(model, "A4")
    );
    expect(getPivotAutofillValue(model, "B4", { direction: "top", steps: 1 })).toBe(
        getCellFormula(model, "B3")
    );
    expect(getPivotAutofillValue(model, "B4", { direction: "top", steps: 2 })).toBe(
        getCellFormula(model, "B2")
    );
    expect(getPivotAutofillValue(model, "B4", { direction: "top", steps: 3 })).toBe(
        getCellFormula(model, "B1")
    );
    // From header to header
    expect(getPivotAutofillValue(model, "B3", { direction: "right", steps: 1 })).toBe(
        getCellFormula(model, "C3")
    );
    expect(getPivotAutofillValue(model, "B3", { direction: "right", steps: 2 })).toBe(
        getCellFormula(model, "D3")
    );
    expect(getPivotAutofillValue(model, "B3", { direction: "left", steps: 1 })).toBe(
        getCellFormula(model, "A3")
    );
    expect(getPivotAutofillValue(model, "B1", { direction: "bottom", steps: 1 })).toBe(
        getCellFormula(model, "B2")
    );
    expect(getPivotAutofillValue(model, "B3", { direction: "top", steps: 1 })).toBe(
        getCellFormula(model, "B2")
    );
    expect(getPivotAutofillValue(model, "A4", { direction: "bottom", steps: 1 })).toBe(
        getCellFormula(model, "A5")
    );
    expect(getPivotAutofillValue(model, "A4", { direction: "top", steps: 1 })).toBe(
        getCellFormula(model, "A3")
    );
    expect(getPivotAutofillValue(model, "A4", { direction: "bottom", steps: 2 })).toBe("");
    expect(getPivotAutofillValue(model, "A4", { direction: "top", steps: 3 })).toBe("");
    // From header to value
    expect(getPivotAutofillValue(model, "B2", { direction: "bottom", steps: 1 })).toBe(
        getCellFormula(model, "B3")
    );
    expect(getPivotAutofillValue(model, "B2", { direction: "bottom", steps: 2 })).toBe(
        getCellFormula(model, "B4")
    );
    expect(getPivotAutofillValue(model, "B2", { direction: "bottom", steps: 4 })).toBe("");
    expect(getPivotAutofillValue(model, "A3", { direction: "right", steps: 1 })).toBe(
        getCellFormula(model, "B3")
    );
    expect(getPivotAutofillValue(model, "A3", { direction: "right", steps: 5 })).toBe(
        getCellFormula(model, "F3")
    );
    expect(getPivotAutofillValue(model, "A3", { direction: "right", steps: 6 })).toBe("");
    // From total row header to value
    expect(getPivotAutofillValue(model, "A5", { direction: "right", steps: 1 })).toBe(
        getCellFormula(model, "B5")
    );
    expect(getPivotAutofillValue(model, "A5", { direction: "right", steps: 5 })).toBe(
        getCellFormula(model, "F5")
    );
});

test("Autofill with pivot positions", async function () {
    const { model } = await createSpreadsheetWithPivot();
    setCellContent(model, "C3", `=PIVOT.VALUE(1,"probability","#bar",1,"#foo",1)`);
    expect(getPivotAutofillValue(model, "C3", { direction: "left", steps: 1 })).toBe(
        `=PIVOT.VALUE(1,"probability","#bar",1,"#foo",0)`
    );
    /** Would be negative => just copy the value */
    expect(getPivotAutofillValue(model, "C3", { direction: "left", steps: 2 })).toBe(
        `=PIVOT.VALUE(1,"probability","#bar",1,"#foo",1)`
    );
    expect(getPivotAutofillValue(model, "C3", { direction: "right", steps: 1 })).toBe(
        `=PIVOT.VALUE(1,"probability","#bar",1,"#foo",2)`
    );
    expect(getPivotAutofillValue(model, "C3", { direction: "right", steps: 10 })).toBe(
        `=PIVOT.VALUE(1,"probability","#bar",1,"#foo",11)`
    );
    expect(getPivotAutofillValue(model, "C3", { direction: "top", steps: 1 })).toBe(
        `=PIVOT.VALUE(1,"probability","#bar",0,"#foo",1)`
    );
    /** Would be negative => just copy the value */
    expect(getPivotAutofillValue(model, "C3", { direction: "top", steps: 2 })).toBe(
        `=PIVOT.VALUE(1,"probability","#bar",1,"#foo",1)`
    );
    expect(getPivotAutofillValue(model, "C3", { direction: "bottom", steps: 1 })).toBe(
        `=PIVOT.VALUE(1,"probability","#bar",2,"#foo",1)`
    );
    expect(
        getPivotAutofillValue(model, "C3", {
            direction: "bottom",
            steps: 10,
        })
    ).toBe(`=PIVOT.VALUE(1,"probability","#bar",11,"#foo",1)`);
});

test("Autofill with references works like any regular function (no custom autofill)", async function () {
    const { model } = await createSpreadsheetWithPivot();
    setCellContent(model, "A1", `=PIVOT.VALUE(1,"probability","bar",B2,"foo",$C$3)`);
    selectCell(model, "A1");

    model.dispatch("AUTOFILL_SELECT", { col: 0, row: 1 });
    model.dispatch("AUTOFILL");
    expect(getCellFormula(model, "A2")).toBe(`=PIVOT.VALUE(1,"probability","bar",B3,"foo",$C$3)`);
});

test("Autofill non-odoo pivot should copy the formula", function () {
    patchTranslations();
    const grid = {
        A1: "Customer",
        B1: "Price",
        C1: `=PIVOT.VALUE(1, "Price")`,
        A2: "Alice",
        B2: "10",
        A3: "",
        B3: "20",
        A4: "Olaf",
        B4: "30",
    };
    const model = createModelFromGrid(grid);
    const pivot = {
        name: "Pivot",
        type: "SPREADSHEET",
        dataSet: {
            zone: toZone("A1:B4"),
            sheetId: model.getters.getActiveSheetId(),
        },
        rows: [{ fieldName: "Customer", order: "asc" }],
        columns: [],
        measures: [{ id: "price", fieldName: "Price", aggregator: "sum" }],
    };
    model.dispatch("ADD_PIVOT", { pivot, pivotId: "1" });
    selectCell(model, "C1");
    model.dispatch("AUTOFILL_SELECT", { col: 2, row: 1 });
    model.dispatch("AUTOFILL");
    expect(getCellFormula(model, "C2")).toBe(`=PIVOT.VALUE(1, "Price")`);
});

test("Can autofill positional col headers horizontally", async () => {
    const { model } = await createSpreadsheetWithPivot({
        arch: /*xml*/ `
                <pivot>
                    <field name="product_id"  type="col"/>
                    <field name="date" interval="month" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
    });
    setCellContent(model, "B1", `=PIVOT.HEADER(1,"#product_id",1)`);
    expect(getPivotAutofillValue(model, "B1", { direction: "right", steps: 1 })).toBe(
        `=PIVOT.HEADER(1,"#product_id",2)`
    );
    selectCell(model, "B1");
    model.dispatch("AUTOFILL_SELECT", { col: 2, row: 0 });
    const tooltipContent = model.getters.getAutofillTooltip().props.content;
    expect(tooltipContent).toEqual([{ value: "xpad" }]);
});

test("Can autofill positional row headers vertically", async () => {
    const { model } = await createSpreadsheetWithPivot({
        arch: /*xml*/ `
                <pivot>
                    <field name="tag_ids" type="col"/>
                    <field name="date" interval="month" type="row"/>
                    <field name="product_id"  type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
    });
    setCellContent(model, "A3", `=PIVOT.HEADER(1,"date:month","04/2016","#product_id",1)`);
    expect(getPivotAutofillValue(model, "A3", { direction: "bottom", steps: 1 })).toBe(
        `=PIVOT.HEADER(1,"date:month","04/2016","#product_id",2)`
    );
    selectCell(model, "A3");
    model.dispatch("AUTOFILL_SELECT", { col: 1, row: 3 });
    const tooltipContent = model.getters.getAutofillTooltip().props.content;
    expect(tooltipContent).toEqual([{ value: "April 2016" }, { value: "" }]);
});

test("Can autofill positional row headers horizontally", async () => {
    const { model } = await createSpreadsheetWithPivot({
        arch: /*xml*/ `
                <pivot>
                    <field name="date" interval="month" type="col"/>
                    <field name="product_id"  type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
    });
    setCellContent(model, "A3", `=PIVOT.HEADER(1,"#product_id",1)`);
    expect(getPivotAutofillValue(model, "A3", { direction: "right", steps: 1 })).toBe(
        `=PIVOT.VALUE(1,"probability:avg","date:month","04/2016")`
    );
    selectCell(model, "A3");
    model.dispatch("AUTOFILL_SELECT", { col: 1, row: 3 });
    const tooltipContent = model.getters.getAutofillTooltip().props.content;
    expect(tooltipContent).toEqual([{ value: "xpad" }]);
});

test("Can autofill positional col horizontally", async () => {
    const { model } = await createSpreadsheetWithPivot({
        arch: /*xml*/ `
                <pivot>
                    <field name="product_id"  type="col"/>
                    <field name="date" interval="month" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
    });
    setCellContent(model, "B1", `=PIVOT.VALUE(1,"probability","#product_id",1)`);
    expect(getPivotAutofillValue(model, "B1", { direction: "right", steps: 1 })).toBe(
        `=PIVOT.VALUE(1,"probability","#product_id",2)`
    );
    selectCell(model, "B1");
    model.dispatch("AUTOFILL_SELECT", { col: 2, row: 0 });
    const tooltipContent = model.getters.getAutofillTooltip().props.content;
    expect(tooltipContent).toEqual([{ value: "xpad" }]);
});

test("Can autofill positional row vertically", async () => {
    const { model } = await createSpreadsheetWithPivot({
        arch: /*xml*/ `
                <pivot>
                    <field name="tag_ids" type="col"/>
                    <field name="date" interval="month" type="row"/>
                    <field name="product_id"  type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
    });
    setCellContent(
        model,
        "A3",
        `=PIVOT.VALUE(1,"probability","date:month","04/2016","#product_id",1)`
    );
    expect(getPivotAutofillValue(model, "A3", { direction: "bottom", steps: 1 })).toBe(
        `=PIVOT.VALUE(1,"probability","date:month","04/2016","#product_id",2)`
    );
    selectCell(model, "A3");
    model.dispatch("AUTOFILL_SELECT", { col: 1, row: 3 });
    const tooltipContent = model.getters.getAutofillTooltip().props.content;
    expect(tooltipContent).toEqual([{ value: "April 2016" }, { value: "" }]);
});
test("Autofill last column cells vertically by targeting col headers", async function () {
    const { model } = await createSpreadsheetWithPivot();
    expect(getPivotAutofillValue(model, "F3", { direction: "top", steps: 1 })).toBe(
        getCellFormula(model, "F2")
    );
    expect(getPivotAutofillValue(model, "F3", { direction: "top", steps: 2 })).toBe(
        getCellFormula(model, "F1")
    );
    expect(getPivotAutofillValue(model, "F5", { direction: "top", steps: 3 })).toBe(
        getCellFormula(model, "F2")
    );
    expect(getPivotAutofillValue(model, "F5", { direction: "top", steps: 4 })).toBe(
        getCellFormula(model, "F1")
    );
    setCellContent(model, "H10", `=PIVOT.VALUE(1,"probability:avg","bar","true")`);
    expect(getPivotAutofillValue(model, "H10", { direction: "top", steps: 5 })).toBe("");
});

test("Autofill pivot values with date in rows", async function () {
    const { model } = await createSpreadsheetWithPivot({
        arch: /*xml*/ `
                <pivot>
                    <field name="foo" type="col"/>
                    <field name="date" interval="month" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
    });
    expect(getPivotAutofillValue(model, "A3", { direction: "bottom", steps: 1 })).toBe(
        getCellFormula(model, "A4").replace("10/2016", "05/2016")
    );
    expect(getPivotAutofillValue(model, "A5", { direction: "bottom", steps: 1 })).toBe(
        '=PIVOT.HEADER(1,"date:month","01/2017")'
    );
    expect(getPivotAutofillValue(model, "B3", { direction: "bottom", steps: 1 })).toBe(
        getCellFormula(model, "B4").replace("10/2016", "05/2016")
    );
    expect(getPivotAutofillValue(model, "B5", { direction: "bottom", steps: 1 })).toBe(
        getCellFormula(model, "B5").replace("12/2016", "01/2017")
    );
    expect(getPivotAutofillValue(model, "B5", { direction: "top", steps: 1 })).toBe(
        getCellFormula(model, "B4").replace("10/2016", "11/2016")
    );
    expect(getPivotAutofillValue(model, "F6", { direction: "top", steps: 1 })).toBe("");
});

test("Autofill pivot values with date in cols", async function () {
    const { model } = await createSpreadsheetWithPivot({
        arch: /*xml*/ `
                <pivot>
                    <field name="foo" type="row"/>
                    <field name="date" interval="day" type="col"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
    });
    expect(getCellFormula(model, "B1")).toBe('=PIVOT.HEADER(1,"date:day","04/14/2016")');
    expect(getPivotAutofillValue(model, "B1", { direction: "right", steps: 1 })).toBe(
        '=PIVOT.HEADER(1,"date:day","04/15/2016")'
    );
    expect(getCellFormula(model, "B2")).toBe(
        '=PIVOT.HEADER(1,"date:day","04/14/2016","measure","probability:avg")'
    );
    expect(getPivotAutofillValue(model, "B2", { direction: "right", steps: 1 })).toBe(
        '=PIVOT.HEADER(1,"date:day","04/15/2016","measure","probability:avg")'
    );
    expect(getCellFormula(model, "B3")).toBe(
        '=PIVOT.VALUE(1,"probability:avg","foo",1,"date:day","04/14/2016")'
    );
    expect(getPivotAutofillValue(model, "B3", { direction: "right", steps: 1 })).toBe(
        '=PIVOT.VALUE(1,"probability:avg","foo",1,"date:day","04/15/2016")'
    );

    setCellContent(model, "C1", '=PIVOT.HEADER(1,"date:day","04/15/2016")');
    expect(getPivotAutofillValue(model, "C1", { direction: "bottom", steps: 1 })).toBe(
        '=PIVOT.HEADER(1,"date:day","04/15/2016","measure","probability:avg")'
    );
    expect(getPivotAutofillValue(model, "C1", { direction: "bottom", steps: 2 })).toBe(
        '=PIVOT.VALUE(1,"probability:avg","foo",1,"date:day","04/15/2016")'
    );
});

test("Autofill pivot values with date in cols and multiple cols", async (assert) => {
    const { model } = await createSpreadsheetWithPivot({
        arch: /*xml*/ `
                <pivot>
                    <field name="date" interval="month" type="col"/>
                    <field name="product_id" type="col"/>
                    <field name="tag_ids" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
    });
    setCellContent(model, "H2", '=PIVOT.HEADER(1,"date:month","05/2016")');
    expect(getPivotAutofillValue(model, "H2", { direction: "bottom", steps: 1 })).toBe("");
    expect(getPivotAutofillValue(model, "H2", { direction: "bottom", steps: 2 })).toBe("");
    expect(getPivotAutofillValue(model, "H2", { direction: "bottom", steps: 3 })).toBe("");
});

test("Autofill pivot values with date (day)", async function () {
    const { model } = await createSpreadsheetWithPivot({
        arch: /*xml*/ `
                <pivot>
                    <field name="foo" type="col"/>
                    <field name="date" interval="day" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
    });
    expect(getCellFormula(model, "A3")).toBe('=PIVOT.HEADER(1,"date:day","04/14/2016")');
    expect(model.getters.getTooltipFormula(getCellFormula(model, "A3"))).toEqual([
        { value: "14 Apr 2016" },
    ]);
    expect(getPivotAutofillValue(model, "A3", { direction: "bottom", steps: 1 })).toBe(
        '=PIVOT.HEADER(1,"date:day","04/15/2016")'
    );
});

test("Autofill pivot values with date (week) 2020 has 53 weeks", async function () {
    const { model } = await createSpreadsheetWithPivot({
        arch: /*xml*/ `
                <pivot>
                    <field name="date" interval="week" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
    });
    setCellContent(model, "A1", '=PIVOT.HEADER(1,"date:week","52/2020")');
    expect(getPivotAutofillValue(model, "A1", { direction: "bottom", steps: 1 })).toBe(
        '=PIVOT.HEADER(1,"date:week","53/2020")'
    );
    expect(model.getters.getTooltipFormula(getCellFormula(model, "A1"))).toEqual([
        { value: "W52 2020" },
    ]);
});

test("Autofill empty pivot date value", async function () {
    const { model, pivotId } = await createSpreadsheetWithPivot({
        arch: /* xml */ `
                <pivot>
                    <field name="date" interval="year" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
    });
    for (const granularity of [
        "day",
        "week",
        "month",
        "quarter",
        "year",
        "quarter_number",
        "month_number",
        "iso_week_number",
        "day_of_month",
    ]) {
        updatePivot(model, pivotId, {
            rows: [{ fieldName: "date", granularity, order: "asc" }],
        });
        await animationFrame();
        setCellContent(model, "A1", `=PIVOT.HEADER(1,"date:${granularity}",FALSE)`);
        expect(getPivotAutofillValue(model, "A1", { direction: "bottom", steps: 1 })).toBe(
            `=PIVOT.HEADER(1,"date:${granularity}",FALSE)`
        );
        expect(model.getters.getTooltipFormula(getCellFormula(model, "A1"))).toEqual([
            { value: "None" },
        ]);
    }
});

test("Autofill past bound pivot date value", async function () {
    const { model, pivotId } = await createSpreadsheetWithPivot({
        arch: /* xml */ `
                <pivot>
                    <field name="date" interval="year" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
    });

    const granularities = [
        ["quarter_number", 1, 4],
        ["month_number", 1, 12],
        ["iso_week_number", 0, 54],
        ["day_of_month", 1, 31],
    ];

    const steps = [1, 10, 20, 30, 40, 50, 60, 70, 80];

    for (const grIdx in granularities) {
        const [granularity, lowerBound, upperBound] = granularities[grIdx];
        updatePivot(model, pivotId, {
            rows: [{ fieldName: "date", granularity, order: "asc" }],
        });
        await animationFrame();
        setCellContent(model, "A1", `=PIVOT.HEADER(1,"date:${granularity}",1)`);
        for (const stepIdx in steps) {
            const step = steps[stepIdx];
            const expectedValue = 1 + step;
            const expectedFormula =
                lowerBound <= expectedValue && expectedValue <= upperBound
                    ? `=PIVOT.HEADER(1,"date:${granularity}",${expectedValue})`
                    : "";
            expect(getPivotAutofillValue(model, "A1", { direction: "bottom", steps: step })).toBe(
                expectedFormula
            );
        }
    }
});

test("Autofill pivot values with date (month)", async function () {
    const { model } = await createSpreadsheetWithPivot({
        arch: /*xml*/ `
                <pivot>
                    <field name="foo" type="col"/>
                    <field name="date" interval="month" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
    });
    expect(getPivotAutofillValue(model, "A3", { direction: "bottom", steps: 1 })).toBe(
        `=PIVOT.HEADER(1,"date:month","05/2016")`
    );
    expect(model.getters.getTooltipFormula(getCellFormula(model, "A3"))).toEqual([
        { value: "April 2016" },
    ]);
});

test("Autofill pivot values with date (quarter)", async function () {
    const { model } = await createSpreadsheetWithPivot({
        arch: /*xml*/ `
                <pivot>
                    <field name="foo" type="col"/>
                    <field name="date" interval="quarter" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
    });
    expect(getPivotAutofillValue(model, "A3", { direction: "bottom", steps: 1 })).toBe(
        getCellFormula(model, "A3").replace("2/2016", "3/2016")
    );
    expect(model.getters.getTooltipFormula(getCellFormula(model, "A3"))).toEqual([
        { value: "Q2 2016" },
    ]);
});

test("Autofill pivot values with date (year)", async function () {
    const { model } = await createSpreadsheetWithPivot({
        arch: /*xml*/ `
                <pivot>
                    <field name="foo" type="col"/>
                    <field name="date" interval="year" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
    });
    expect(getPivotAutofillValue(model, "A3", { direction: "bottom", steps: 1 })).toBe(
        getCellFormula(model, "A3").replace("2016", "2017")
    );
    expect(model.getters.getTooltipFormula(getCellFormula(model, "A3"))).toEqual([
        { value: "2016" },
    ]);
});

test("Autofill pivot values with date (no defined interval)", async function () {
    const { model } = await createSpreadsheetWithPivot({
        arch: /*xml*/ `
                <pivot>
                    <field name="foo" type="col"/>
                    <field name="date" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
    });
    expect(getPivotAutofillValue(model, "A3", { direction: "bottom", steps: 1 })).toBe(
        `=PIVOT.HEADER(1,"date:month","05/2016")`
    );
});

test("Tooltip of pivot formulas", async function () {
    const { model } = await createSpreadsheetWithPivot({
        arch: /*xml*/ `
                <pivot>
                    <field name="foo" type="col"/>
                    <field name="date" interval="year" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
    });
    expect(model.getters.getTooltipFormula(getCellFormula(model, "A3"))).toEqual([
        { value: "2016" },
    ]);
    expect(model.getters.getTooltipFormula(getCellFormula(model, "B3"))).toEqual([
        { value: "2016" },
    ]);
    expect(model.getters.getTooltipFormula(getCellFormula(model, "E3"))).toEqual([
        { value: "2016" },
    ]);
    expect(model.getters.getTooltipFormula(getCellFormula(model, "F3"))).toEqual([
        { value: "2016" },
    ]);
    expect(model.getters.getTooltipFormula(getCellFormula(model, "B1"))).toEqual([{ value: "1" }]);
    expect(model.getters.getTooltipFormula(getCellFormula(model, "B2"))).toEqual([
        { value: "1" },
        { value: "Probability" },
    ]);
    expect(model.getters.getTooltipFormula(`=PIVOT.HEADER("1")`, true)).toEqual([
        { value: "Total" },
    ]);
    expect(model.getters.getTooltipFormula(`=PIVOT.HEADER("1")`, false)).toEqual([
        { value: "Total" },
    ]);
});

test("Tooltip of pivot formulas with 2 measures", async function () {
    const { model } = await createSpreadsheetWithPivot({
        arch: /*xml*/ `
                <pivot>
                    <field name="name" type="col"/>
                    <field name="date" interval="year" type="row"/>
                    <field name="probability" type="measure"/>
                    <field name="foo" type="measure"/>
                </pivot>`,
    });
    expect(model.getters.getTooltipFormula(getCellFormula(model, "A3"))).toEqual([
        { value: "2016" },
    ]);
    expect(model.getters.getTooltipFormula(getCellFormula(model, "B3"))).toEqual([
        { value: "2016" },
    ]);
    expect(model.getters.getTooltipFormula(getCellFormula(model, "C3"), true)).toEqual([
        { value: "None" },
        { value: "Foo" },
    ]);
});

test("Tooltip of empty pivot formula is empty", async function () {
    const { model } = await createSpreadsheetWithPivot({
        arch: /*xml*/ `
                <pivot>
                    <field name="name" type="col"/>
                    <field name="date" interval="year" type="row"/>
                    <field name="probability" type="measure"/>
                    <field name="foo" type="measure"/>
                </pivot>`,
    });
    selectCell(model, "A3");
    model.dispatch("AUTOFILL_SELECT", { col: 10, row: 10 });
    expect(model.getters.getAutofillTooltip()).toBe(undefined);
});

test("Autofill content which contains pivots but which is not a pivot", async function () {
    const { model } = await createSpreadsheetWithPivot({
        arch: /*xml*/ `
                <pivot>
                    <field name="foo" type="col"/>
                    <field name="date" interval="year" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
    });
    const a3 = getCellFormula(model, "A3").replace("=", "");
    const content = `=${a3} + ${a3}`;
    setCellContent(model, "F6", content);
    expect(getPivotAutofillValue(model, "F6", { direction: "bottom", steps: 1 })).toBe(content);
    expect(getPivotAutofillValue(model, "F6", { direction: "right", steps: 1 })).toBe(content);
});

test("Autofill pivot formula with missing pivotId", async function () {
    patchTranslations();
    const model = new spreadsheet.Model({
        sheets: [
            {
                colNumber: 1,
                rowNumber: 2,
                cells: {
                    A1: { content: '=PIVOT.VALUE("1","bar","date","05/2023")' },
                    B1: { content: '=PIVOT.HEADER("1","date","05/2023")' },
                },
            },
        ],
    });
    expect(getPivotAutofillValue(model, "A1", { direction: "bottom", steps: 1 })).toBe(
        '=PIVOT.VALUE("1","bar","date","05/2023")'
    );
    expect(getPivotAutofillValue(model, "B1", { direction: "bottom", steps: 1 })).toBe(
        '=PIVOT.HEADER("1","date","05/2023")'
    );
    expect(model.getters.getTooltipFormula(getCellFormula(model, "A1"), false)).toEqual([
        {
            title: "Missing pivot",
            value: "Missing pivot #1",
        },
    ]);
    expect(model.getters.getTooltipFormula(getCellFormula(model, "B1"), false)).toEqual([
        {
            title: "Missing pivot",
            value: "Missing pivot #1",
        },
    ]);
});

test("Can autofill col headers horizontally", async () => {
    const { model } = await createSpreadsheetWithPivot({
        arch: /*xml*/ `
                <pivot>
                    <field name="tag_ids" type="col"/>
                    <field name="date" interval="year" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
    });
    const sortedTagNames = ["isCool", "Growing", "None"];
    selectCell(model, "B1");
    model.dispatch("AUTOFILL_SELECT", { col: 2, row: 0 });
    let tooltipContent;
    tooltipContent = model.getters.getAutofillTooltip().props.content;
    expect(tooltipContent[tooltipContent.length - 1].value).toBe(sortedTagNames[1]);
    selectCell(model, "C1");
    model.dispatch("AUTOFILL_SELECT", { col: 3, row: 0 });
    tooltipContent = model.getters.getAutofillTooltip().props.content;
    expect(tooltipContent[tooltipContent.length - 1].value).toBe(sortedTagNames[2]);
    selectCell(model, "D1");
    model.dispatch("AUTOFILL_SELECT", { col: 4, row: 0 });
    tooltipContent = model.getters.getAutofillTooltip().props.content;
    expect(tooltipContent[tooltipContent.length - 1].value).toBe("Total");
    selectCell(model, "E1");
    model.dispatch("AUTOFILL_SELECT", { col: 5, row: 0 });
    tooltipContent = model.getters.getAutofillTooltip().props.content;
    expect(tooltipContent[tooltipContent.length - 1].value).toBe(sortedTagNames[0]);
});

test("Can autofill col headers vertically", async () => {
    const { model } = await createSpreadsheetWithPivot({
        arch: /*xml*/ `
                <pivot>
                    <field name="tag_ids" type="col"/>
                    <field name="date" interval="year" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
    });

    selectCell(model, "B1");
    model.dispatch("AUTOFILL_SELECT", { col: 1, row: 1 });
    let tooltipContent;
    tooltipContent = model.getters.getAutofillTooltip().props.content;
    expect(tooltipContent[tooltipContent.length - 1].value).toBe("Probability");
    model.dispatch("AUTOFILL_SELECT", { col: 1, row: 2 });
    tooltipContent = model.getters.getAutofillTooltip().props.content;
    expect(tooltipContent[tooltipContent.length - 1].value).toBe("2016");
    selectCell(model, "C1");
    model.dispatch("AUTOFILL_SELECT", { col: 2, row: 1 });
    tooltipContent = model.getters.getAutofillTooltip().props.content;
    expect(tooltipContent[tooltipContent.length - 1].value).toBe("Probability");
    model.dispatch("AUTOFILL_SELECT", { col: 2, row: 2 });
    tooltipContent = model.getters.getAutofillTooltip().props.content;
    expect(tooltipContent[tooltipContent.length - 1].value).toBe("2016");
    selectCell(model, "D1");
    model.dispatch("AUTOFILL_SELECT", { col: 3, row: 1 });
    tooltipContent = model.getters.getAutofillTooltip().props.content;
    expect(tooltipContent[tooltipContent.length - 1].value).toBe("Probability");
    model.dispatch("AUTOFILL_SELECT", { col: 3, row: 2 });
    tooltipContent = model.getters.getAutofillTooltip().props.content;
    expect(tooltipContent[tooltipContent.length - 1].value).toBe("2016");
    selectCell(model, "E1");
    model.dispatch("AUTOFILL_SELECT", { col: 4, row: 1 });
    tooltipContent = model.getters.getAutofillTooltip().props.content;
    expect(tooltipContent[tooltipContent.length - 1].value).toBe("Probability");
    model.dispatch("AUTOFILL_SELECT", { col: 4, row: 2 });
    tooltipContent = model.getters.getAutofillTooltip().props.content;
    expect(tooltipContent[tooltipContent.length - 1].value).toBe("2016");
    model.dispatch("AUTOFILL_SELECT", { col: 4, row: 3 });
    tooltipContent = model.getters.getAutofillTooltip().props.content;
    expect(tooltipContent[tooltipContent.length - 1].value).toBe("Total");
});

test("Can autofill row headers horizontally", async () => {
    const { model } = await createSpreadsheetWithPivot({
        arch: /*xml*/ `
                <pivot>
                    <field name="tag_ids" type="col"/>
                    <field name="date" interval="month" type="row"/>
                    <field name="product_id"  type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
    });
    const sortedTagNames = ["isCool", "Growing", "None"];
    let tooltipContent;
    selectCell(model, "A3");
    model.dispatch("AUTOFILL_SELECT", { col: 1, row: 2 });
    tooltipContent = model.getters.getAutofillTooltip().props.content;
    expect(tooltipContent[tooltipContent.length - 1].value).toBe(sortedTagNames[0]);
    selectCell(model, "A4");
    model.dispatch("AUTOFILL_SELECT", { col: 2, row: 3 });
    tooltipContent = model.getters.getAutofillTooltip().props.content;
    expect(tooltipContent[tooltipContent.length - 1].value).toBe(sortedTagNames[1]);
    selectCell(model, "A5");
    model.dispatch("AUTOFILL_SELECT", { col: 1, row: 4 });
    tooltipContent = model.getters.getAutofillTooltip().props.content;
    expect(tooltipContent[tooltipContent.length - 1].value).toBe(sortedTagNames[0]);
    selectCell(model, "A6");
    model.dispatch("AUTOFILL_SELECT", { col: 3, row: 5 });
    tooltipContent = model.getters.getAutofillTooltip().props.content;
    expect(tooltipContent[tooltipContent.length - 1].value).toBe(sortedTagNames[2]);
    selectCell(model, "A7");
    model.dispatch("AUTOFILL_SELECT", { col: 1, row: 6 });
    tooltipContent = model.getters.getAutofillTooltip().props.content;
    expect(tooltipContent[tooltipContent.length - 1].value).toBe(sortedTagNames[0]);
    selectCell(model, "A8");
    model.dispatch("AUTOFILL_SELECT", { col: 4, row: 7 });
    tooltipContent = model.getters.getAutofillTooltip().props.content;
    expect(tooltipContent[tooltipContent.length - 1].value).toBe("Total");
    selectCell(model, "A9");
    model.dispatch("AUTOFILL_SELECT", { col: 1, row: 8 });
    tooltipContent = model.getters.getAutofillTooltip().props.content;
    expect(tooltipContent[tooltipContent.length - 1].value).toBe(sortedTagNames[0]);
});

test("Can autofill row headers vertically", async () => {
    const { model } = await createSpreadsheetWithPivot({
        arch: /*xml*/ `
                <pivot>
                    <field name="tag_ids" type="col"/>
                    <field name="date" interval="month" type="row"/>
                    <field name="product_id"  type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
    });
    let tooltipContent;
    selectCell(model, "A3");
    model.dispatch("AUTOFILL_SELECT", { col: 0, row: 3 });
    tooltipContent = model.getters.getAutofillTooltip().props.content;
    expect(tooltipContent[tooltipContent.length - 1].value).toBe("xphone");
    selectCell(model, "A4");
    model.dispatch("AUTOFILL_SELECT", { col: 0, row: 4 });
    tooltipContent = model.getters.getAutofillTooltip().props.content;
    expect(tooltipContent[tooltipContent.length - 1].value).toBe("October 2016");
    selectCell(model, "A5");
    model.dispatch("AUTOFILL_SELECT", { col: 0, row: 5 });
    tooltipContent = model.getters.getAutofillTooltip().props.content;
    expect(tooltipContent[tooltipContent.length - 1].value).toBe("xpad");
    selectCell(model, "A6");
    model.dispatch("AUTOFILL_SELECT", { col: 0, row: 6 });
    tooltipContent = model.getters.getAutofillTooltip().props.content;
    expect(tooltipContent[tooltipContent.length - 1].value).toBe("December 2016");
    selectCell(model, "A7");
    model.dispatch("AUTOFILL_SELECT", { col: 0, row: 7 });
    tooltipContent = model.getters.getAutofillTooltip().props.content;
    expect(tooltipContent[tooltipContent.length - 1].value).toBe("xpad");
    selectCell(model, "A8");
    model.dispatch("AUTOFILL_SELECT", { col: 0, row: 8 });
    tooltipContent = model.getters.getAutofillTooltip().props.content;
    expect(tooltipContent[tooltipContent.length - 1].value).toBe("Total");
    selectCell(model, "A9");
    model.dispatch("AUTOFILL_SELECT", { col: 0, row: 9 });
    tooltipContent = model.getters.getAutofillTooltip().props.content;
    expect(tooltipContent[tooltipContent.length - 1].value).toBe("Probability");
});

test("Autofill pivot keeps format but neither style nor border", async function () {
    const { model } = await createSpreadsheetWithPivot({
        arch: /*xml*/ `
                <pivot>
                    <field name="date" type="col"/>
                    <field name="product_id"  type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
    });

    // Change the format, style and borders of E3
    const sheetId = model.getters.getActiveSheetId();
    const { col, row } = toCartesian("E3");
    const border = {
        left: { style: "thin", color: "#000" },
    };
    const style = { textColor: "orange" };
    setCellStyle(model, "E3", style);
    setCellFormat(model, "E3", "#,##0.0");
    model.dispatch("SET_BORDER", { sheetId, col, row, border });

    // Change the format of E4
    setCellFormat(model, "E4", "#,##0.000");

    // Check that the format, style and border of E3 have been correctly applied
    autofill(model, "E3", "E4");
    const startingCell = getCell(model, "E3");
    expect(startingCell.style).toEqual(style);
    expect(model.getters.getCellBorder({ sheetId, col, row }).left).toEqual(border.left);
    expect(startingCell.format).toBe("#,##0.0");

    // Check that the format of E3 has been correctly applied to E4 but not the style nor the border
    const filledCell = getCell(model, "E4");
    expect(filledCell.style).toBe(undefined);
    expect(model.getters.getCellBorder({ sheetId, col, row: row + 1 })).toBe(null);
    expect(filledCell.format).toBe("#,##0.0");
});

test("Can autofill pivot horizontally with column grouped by date", async () => {
    const { model } = await createSpreadsheetWithPivot({
        arch: /*xml*/ `
                <pivot>
                    <field name="date" interval="month" type="col"/>
                    <field name="product_id"  type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
    });
    // Headers
    setCellContent(
        model,
        "B1",
        `=PIVOT.HEADER(1,"date:month","04/2016","measure","probability:avg")`
    );
    expect(getPivotAutofillValue(model, "B1", { direction: "right", steps: 1 })).toBe(
        `=PIVOT.HEADER(1,"date:month","05/2016","measure","probability:avg")`
    );

    setCellContent(model, "B1", `=PIVOT.HEADER(1,"measure","probability:avg")`);
    expect(getPivotAutofillValue(model, "B1", { direction: "right", steps: 1 })).toBe("");

    // Values
    setCellContent(
        model,
        "B1",
        `=PIVOT.VALUE(1,"probability:avg","product_id",47,"date:month","04/2016")`
    );
    expect(getPivotAutofillValue(model, "B1", { direction: "right", steps: 1 })).toBe(
        `=PIVOT.VALUE(1,"probability:avg","product_id",47,"date:month","05/2016")`
    );

    setCellContent(model, "B1", `=PIVOT.VALUE(1,"probability:avg","product_id",47)`);
    expect(getPivotAutofillValue(model, "B1", { direction: "right", steps: 1 })).toBe("");
});

test("Autofill does not crash when autofilling wrong relational id", async () => {
    const { model } = await createSpreadsheetWithPivot({
        arch: /*xml*/ `
                <pivot>
                    <field name="product_id"  type="col"/>
                    <field name="date" interval="month" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
    });
    const formula = `=PIVOT.HEADER(1,"product_id",9999)`;
    expect(model.getters.getTooltipFormula(formula)).toEqual([{ value: "Unknown" }]);
});
