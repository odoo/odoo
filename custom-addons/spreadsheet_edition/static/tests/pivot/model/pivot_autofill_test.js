/** @odoo-module  */

import * as spreadsheet from "@odoo/o-spreadsheet";
const { toCartesian } = spreadsheet.helpers;
import {
    autofill,
    selectCell,
    setCellContent,
    setCellFormat,
    setCellStyle,
} from "@spreadsheet/../tests/utils/commands";
import { getCellFormula, getCell } from "@spreadsheet/../tests/utils/getters";
import { createSpreadsheetWithPivot } from "@spreadsheet/../tests/utils/pivot";

/**
 * Get the computed value that would be autofilled starting from the given xc.
 * The starting xc should contains a Pivot formula
 */
export function getPivotAutofillValue(model, xc, { direction, steps }) {
    const content = getCellFormula(model, xc);
    const column = ["left", "right"].includes(direction);
    const increment = ["left", "top"].includes(direction) ? -steps : steps;
    return model.getters.getPivotNextAutofillValue(content, column, increment);
}

QUnit.module("spreadsheet > pivot_autofill", {}, () => {
    QUnit.test("Autofill pivot values", async function (assert) {
        assert.expect(28);

        const { model } = await createSpreadsheetWithPivot();

        // From value to value
        assert.strictEqual(
            getPivotAutofillValue(model, "C3", { direction: "bottom", steps: 1 }),
            getCellFormula(model, "C4")
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "B4", { direction: "top", steps: 1 }),
            getCellFormula(model, "B3")
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "C3", { direction: "right", steps: 1 }),
            getCellFormula(model, "D3")
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "C3", { direction: "left", steps: 1 }),
            getCellFormula(model, "B3")
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "C3", { direction: "bottom", steps: 2 }),
            getCellFormula(model, "C5")
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "C3", { direction: "bottom", steps: 3 }),
            ""
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "C3", { direction: "right", steps: 4 }),
            ""
        );
        // From value to header
        assert.strictEqual(
            getPivotAutofillValue(model, "B4", { direction: "left", steps: 1 }),
            getCellFormula(model, "A4")
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "B4", { direction: "top", steps: 1 }),
            getCellFormula(model, "B3")
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "B4", { direction: "top", steps: 2 }),
            getCellFormula(model, "B2")
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "B4", { direction: "top", steps: 3 }),
            getCellFormula(model, "B1")
        );
        // From header to header
        assert.strictEqual(
            getPivotAutofillValue(model, "B3", { direction: "right", steps: 1 }),
            getCellFormula(model, "C3")
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "B3", { direction: "right", steps: 2 }),
            getCellFormula(model, "D3")
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "B3", { direction: "left", steps: 1 }),
            getCellFormula(model, "A3")
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "B1", { direction: "bottom", steps: 1 }),
            getCellFormula(model, "B2")
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "B3", { direction: "top", steps: 1 }),
            getCellFormula(model, "B2")
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "A4", { direction: "bottom", steps: 1 }),
            getCellFormula(model, "A5")
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "A4", { direction: "top", steps: 1 }),
            getCellFormula(model, "A3")
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "A4", { direction: "bottom", steps: 2 }),
            ""
        );
        assert.strictEqual(getPivotAutofillValue(model, "A4", { direction: "top", steps: 3 }), "");
        // From header to value
        assert.strictEqual(
            getPivotAutofillValue(model, "B2", { direction: "bottom", steps: 1 }),
            getCellFormula(model, "B3")
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "B2", { direction: "bottom", steps: 2 }),
            getCellFormula(model, "B4")
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "B2", { direction: "bottom", steps: 4 }),
            ""
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "A3", { direction: "right", steps: 1 }),
            getCellFormula(model, "B3")
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "A3", { direction: "right", steps: 5 }),
            getCellFormula(model, "F3")
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "A3", { direction: "right", steps: 6 }),
            ""
        );
        // From total row header to value
        assert.strictEqual(
            getPivotAutofillValue(model, "A5", { direction: "right", steps: 1 }),
            getCellFormula(model, "B5")
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "A5", { direction: "right", steps: 5 }),
            getCellFormula(model, "F5")
        );
    });

    QUnit.test("Autofill with pivot positions", async function (assert) {
        const { model } = await createSpreadsheetWithPivot();
        setCellContent(model, "C3", `=ODOO.PIVOT(1,"probability","#bar",1,"#foo",1)`);
        assert.strictEqual(
            getPivotAutofillValue(model, "C3", { direction: "left", steps: 1 }),
            `=ODOO.PIVOT(1,"probability","#bar",1,"#foo",0)`
        );
        /** Would be negative => just copy the value */
        assert.strictEqual(
            getPivotAutofillValue(model, "C3", { direction: "left", steps: 2 }),
            `=ODOO.PIVOT(1,"probability","#bar",1,"#foo",1)`
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "C3", { direction: "right", steps: 1 }),
            `=ODOO.PIVOT(1,"probability","#bar",1,"#foo",2)`
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "C3", { direction: "right", steps: 10 }),
            `=ODOO.PIVOT(1,"probability","#bar",1,"#foo",11)`
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "C3", { direction: "top", steps: 1 }),
            `=ODOO.PIVOT(1,"probability","#bar",0,"#foo",1)`
        );
        /** Would be negative => just copy the value */
        assert.strictEqual(
            getPivotAutofillValue(model, "C3", { direction: "top", steps: 2 }),
            `=ODOO.PIVOT(1,"probability","#bar",1,"#foo",1)`
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "C3", { direction: "bottom", steps: 1 }),
            `=ODOO.PIVOT(1,"probability","#bar",2,"#foo",1)`
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "C3", {
                direction: "bottom",
                steps: 10,
            }),
            `=ODOO.PIVOT(1,"probability","#bar",11,"#foo",1)`
        );
    });

    QUnit.test(
        "Autofill with references works like any regular function (no custom autofill)",
        async function (assert) {
            const { model } = await createSpreadsheetWithPivot();
            setCellContent(model, "A1", `=ODOO.PIVOT(1,"probability","bar",B2,"foo",$C$3)`);
            selectCell(model, "A1");

            model.dispatch("AUTOFILL_SELECT", { col: 0, row: 1 });
            model.dispatch("AUTOFILL");
            assert.equal(
                getCellFormula(model, "A2"),
                `=ODOO.PIVOT(1,"probability","bar",B3,"foo",$C$3)`
            );
        }
    );

    QUnit.test("Can autofill positional col headers horizontally", async (assert) => {
        const { model } = await createSpreadsheetWithPivot({
            arch: /*xml*/ `
                <pivot>
                    <field name="product_id"  type="col"/>
                    <field name="date" interval="month" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
        });
        setCellContent(model, "B1", `=ODOO.PIVOT.HEADER(1,"#product_id",1)`);
        assert.strictEqual(
            getPivotAutofillValue(model, "B1", { direction: "right", steps: 1 }),
            `=ODOO.PIVOT.HEADER(1,"#product_id",2)`
        );
        selectCell(model, "B1");
        model.dispatch("AUTOFILL_SELECT", { col: 2, row: 0 });
        const tooltipContent = model.getters.getAutofillTooltip().props.content;
        assert.deepEqual(tooltipContent, [{ value: "xpad" }]);
    });

    QUnit.test("Can autofill positional row headers vertically", async (assert) => {
        const { model } = await createSpreadsheetWithPivot({
            arch: /*xml*/ `
                <pivot>
                    <field name="tag_ids" type="col"/>
                    <field name="date" interval="month" type="row"/>
                    <field name="product_id"  type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
        });
        setCellContent(model, "A3", `=ODOO.PIVOT.HEADER(1,"date:month","04/2016","#product_id",1)`);
        assert.strictEqual(
            getPivotAutofillValue(model, "A3", { direction: "bottom", steps: 1 }),
            `=ODOO.PIVOT.HEADER(1,"date:month","04/2016","#product_id",2)`
        );
        selectCell(model, "A3");
        model.dispatch("AUTOFILL_SELECT", { col: 1, row: 3 });
        const tooltipContent = model.getters.getAutofillTooltip().props.content;
        assert.deepEqual(tooltipContent, [{ value: "April 2016" }, { value: "" }]);
    });

    QUnit.test("Can autofill positional col horizontally", async (assert) => {
        const { model } = await createSpreadsheetWithPivot({
            arch: /*xml*/ `
                <pivot>
                    <field name="product_id"  type="col"/>
                    <field name="date" interval="month" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
        });
        setCellContent(model, "B1", `=ODOO.PIVOT(1,"probability","#product_id",1)`);
        assert.strictEqual(
            getPivotAutofillValue(model, "B1", { direction: "right", steps: 1 }),
            `=ODOO.PIVOT(1,"probability","#product_id",2)`
        );
        selectCell(model, "B1");
        model.dispatch("AUTOFILL_SELECT", { col: 2, row: 0 });
        const tooltipContent = model.getters.getAutofillTooltip().props.content;
        assert.deepEqual(tooltipContent, [{ value: "xpad" }]);
    });

    QUnit.test("Can autofill positional row vertically", async (assert) => {
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
            `=ODOO.PIVOT(1,"probability","date:month","04/2016","#product_id",1)`
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "A3", { direction: "bottom", steps: 1 }),
            `=ODOO.PIVOT(1,"probability","date:month","04/2016","#product_id",2)`
        );
        selectCell(model, "A3");
        model.dispatch("AUTOFILL_SELECT", { col: 1, row: 3 });
        const tooltipContent = model.getters.getAutofillTooltip().props.content;
        assert.deepEqual(tooltipContent, [{ value: "April 2016" }, { value: "" }]);
    });
    QUnit.test(
        "Autofill last column cells vertically by targeting col headers",
        async function (assert) {
            const { model } = await createSpreadsheetWithPivot();
            assert.strictEqual(
                getPivotAutofillValue(model, "F3", { direction: "top", steps: 1 }),
                getCellFormula(model, "F2")
            );
            assert.strictEqual(
                getPivotAutofillValue(model, "F3", { direction: "top", steps: 2 }),
                getCellFormula(model, "F1")
            );
            assert.strictEqual(
                getPivotAutofillValue(model, "F5", { direction: "top", steps: 3 }),
                getCellFormula(model, "F2")
            );
            assert.strictEqual(
                getPivotAutofillValue(model, "F5", { direction: "top", steps: 4 }),
                getCellFormula(model, "F1")
            );
            setCellContent(model, "H10", `=ODOO.PIVOT(1,"probability","bar","true")`);
            assert.strictEqual(
                getPivotAutofillValue(model, "H10", { direction: "top", steps: 5 }),
                ""
            );
        }
    );

    QUnit.test("Autofill pivot values with date in rows", async function (assert) {
        assert.expect(6);

        const { model } = await createSpreadsheetWithPivot({
            arch: /*xml*/ `
                <pivot>
                    <field name="foo" type="col"/>
                    <field name="date" interval="month" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
        });
        assert.strictEqual(
            getPivotAutofillValue(model, "A3", { direction: "bottom", steps: 1 }),
            getCellFormula(model, "A4").replace("10/2016", "05/2016")
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "A5", { direction: "bottom", steps: 1 }),
            '=ODOO.PIVOT.HEADER(1,"date:month","01/2017")'
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "B3", { direction: "bottom", steps: 1 }),
            getCellFormula(model, "B4").replace("10/2016", "05/2016")
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "B5", { direction: "bottom", steps: 1 }),
            getCellFormula(model, "B5").replace("12/2016", "01/2017")
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "B5", { direction: "top", steps: 1 }),
            getCellFormula(model, "B4").replace("10/2016", "11/2016")
        );
        assert.strictEqual(getPivotAutofillValue(model, "F6", { direction: "top", steps: 1 }), "");
    });

    QUnit.test("Autofill pivot values with date in cols", async function (assert) {
        const { model } = await createSpreadsheetWithPivot({
            arch: /*xml*/ `
                <pivot>
                    <field name="foo" type="row"/>
                    <field name="date" interval="day" type="col"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
        });
        assert.strictEqual(
            getCellFormula(model, "B1"),
            '=ODOO.PIVOT.HEADER(1,"date:day","04/14/2016")'
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "B1", { direction: "right", steps: 1 }),
            '=ODOO.PIVOT.HEADER(1,"date:day","04/15/2016")'
        );
        assert.strictEqual(
            getCellFormula(model, "B2"),
            '=ODOO.PIVOT.HEADER(1,"date:day","04/14/2016","measure","probability")'
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "B2", { direction: "right", steps: 1 }),
            '=ODOO.PIVOT.HEADER(1,"date:day","04/15/2016","measure","probability")'
        );
        assert.strictEqual(
            getCellFormula(model, "B3"),
            '=ODOO.PIVOT(1,"probability","foo",1,"date:day","04/14/2016")'
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "B3", { direction: "right", steps: 1 }),
            '=ODOO.PIVOT(1,"probability","foo",1,"date:day","04/15/2016")'
        );
    });

    QUnit.test("Autofill pivot values with date (day)", async function (assert) {
        const { model } = await createSpreadsheetWithPivot({
            arch: /*xml*/ `
                <pivot>
                    <field name="foo" type="col"/>
                    <field name="date" interval="day" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
        });
        assert.strictEqual(
            getCellFormula(model, "A3"),
            '=ODOO.PIVOT.HEADER(1,"date:day","04/14/2016")'
        );
        assert.deepEqual(model.getters.getTooltipFormula(getCellFormula(model, "A3")), [
            { value: "4/14/2016" },
        ]);
        assert.strictEqual(
            getPivotAutofillValue(model, "A3", { direction: "bottom", steps: 1 }),
            '=ODOO.PIVOT.HEADER(1,"date:day","04/15/2016")'
        );
    });

    QUnit.test("Autofill pivot values with date (week) 2020 has 53 weeks", async function (assert) {
        const { model } = await createSpreadsheetWithPivot({
            arch: /*xml*/ `
                <pivot>
                    <field name="date" interval="week" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
        });
        setCellContent(model, "A1", '=ODOO.PIVOT.HEADER(1,"date:week","52/2020")');
        assert.strictEqual(
            getPivotAutofillValue(model, "A1", { direction: "bottom", steps: 1 }),
            '=ODOO.PIVOT.HEADER(1,"date:week","53/2020")'
        );
        assert.deepEqual(model.getters.getTooltipFormula(getCellFormula(model, "A1")), [
            { value: "W52 2020" },
        ]);
    });

    QUnit.test("Autofill empty pivot date value", async function (assert) {
        for (const interval of ["day", "week", "month", "quarter", "year"]) {
            const { model } = await createSpreadsheetWithPivot({
                arch: /* xml */ `
                    <pivot>
                        <field name="date" interval="${interval}" type="row"/>
                        <field name="probability" type="measure"/>
                    </pivot>`,
            });
            setCellContent(model, "A1", `=ODOO.PIVOT.HEADER(1,"date:${interval}","false")`);
            assert.strictEqual(
                getPivotAutofillValue(model, "A1", { direction: "bottom", steps: 1 }),
                `=ODOO.PIVOT.HEADER(1,"date:${interval}","false")`
            );
            assert.deepEqual(model.getters.getTooltipFormula(getCellFormula(model, "A1")), [
                { value: "None" },
            ]);
        }
    });

    QUnit.test("Autofill pivot values with date (month)", async function (assert) {
        const { model } = await createSpreadsheetWithPivot({
            arch: /*xml*/ `
                <pivot>
                    <field name="foo" type="col"/>
                    <field name="date" interval="month" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
        });
        assert.strictEqual(
            getPivotAutofillValue(model, "A3", { direction: "bottom", steps: 1 }),
            `=ODOO.PIVOT.HEADER(1,"date:month","05/2016")`
        );
        assert.deepEqual(model.getters.getTooltipFormula(getCellFormula(model, "A3")), [
            { value: "April 2016" },
        ]);
    });

    QUnit.test("Autofill pivot values with date (quarter)", async function (assert) {
        const { model } = await createSpreadsheetWithPivot({
            arch: /*xml*/ `
                <pivot>
                    <field name="foo" type="col"/>
                    <field name="date" interval="quarter" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
        });
        assert.strictEqual(
            getPivotAutofillValue(model, "A3", { direction: "bottom", steps: 1 }),
            getCellFormula(model, "A3").replace("2/2016", "3/2016")
        );
        assert.deepEqual(model.getters.getTooltipFormula(getCellFormula(model, "A3")), [
            { value: "Q2 2016" },
        ]);
    });

    QUnit.test("Autofill pivot values with date (year)", async function (assert) {
        const { model } = await createSpreadsheetWithPivot({
            arch: /*xml*/ `
                <pivot>
                    <field name="foo" type="col"/>
                    <field name="date" interval="year" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
        });
        assert.strictEqual(
            getPivotAutofillValue(model, "A3", { direction: "bottom", steps: 1 }),
            getCellFormula(model, "A3").replace("2016", "2017")
        );
        assert.deepEqual(model.getters.getTooltipFormula(getCellFormula(model, "A3")), [
            { value: "2016" },
        ]);
    });

    QUnit.test("Autofill pivot values with date (no defined interval)", async function (assert) {
        const { model } = await createSpreadsheetWithPivot({
            arch: /*xml*/ `
                <pivot>
                    <field name="foo" type="col"/>
                    <field name="date" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
        });
        assert.strictEqual(
            getPivotAutofillValue(model, "A3", { direction: "bottom", steps: 1 }),
            `=ODOO.PIVOT.HEADER(1,"date","05/2016")`
        );
    });

    QUnit.test("Tooltip of pivot formulas", async function (assert) {
        assert.expect(8);

        const { model } = await createSpreadsheetWithPivot({
            arch: /*xml*/ `
                <pivot>
                    <field name="foo" type="col"/>
                    <field name="date" interval="year" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
        });
        assert.deepEqual(model.getters.getTooltipFormula(getCellFormula(model, "A3")), [
            { value: "2016" },
        ]);
        assert.deepEqual(model.getters.getTooltipFormula(getCellFormula(model, "B3")), [
            { value: "2016" },
        ]);
        assert.deepEqual(model.getters.getTooltipFormula(getCellFormula(model, "E3")), [
            { value: "2016" },
        ]);
        assert.deepEqual(model.getters.getTooltipFormula(getCellFormula(model, "F3")), [
            { value: "2016" },
        ]);
        assert.deepEqual(model.getters.getTooltipFormula(getCellFormula(model, "B1")), [
            { value: "1" },
        ]);
        assert.deepEqual(model.getters.getTooltipFormula(getCellFormula(model, "B2")), [
            { value: "1" },
            { value: "Probability" },
        ]);
        assert.deepEqual(model.getters.getTooltipFormula(`=ODOO.PIVOT.HEADER("1")`, true), [
            { value: "Total" },
        ]);
        assert.deepEqual(model.getters.getTooltipFormula(`=ODOO.PIVOT.HEADER("1")`, false), [
            { value: "Total" },
        ]);
    });

    QUnit.test("Tooltip of pivot formulas with 2 measures", async function (assert) {
        assert.expect(3);

        const { model } = await createSpreadsheetWithPivot({
            arch: /*xml*/ `
                <pivot>
                    <field name="name" type="col"/>
                    <field name="date" interval="year" type="row"/>
                    <field name="probability" type="measure"/>
                    <field name="foo" type="measure"/>
                </pivot>`,
        });
        assert.deepEqual(model.getters.getTooltipFormula(getCellFormula(model, "A3")), [
            { value: "2016" },
        ]);
        assert.deepEqual(model.getters.getTooltipFormula(getCellFormula(model, "B3")), [
            { value: "2016" },
        ]);
        assert.deepEqual(model.getters.getTooltipFormula(getCellFormula(model, "C3"), true), [
            { value: "None" },
            { value: "Foo" },
        ]);
    });

    QUnit.test("Tooltip of empty pivot formula is empty", async function (assert) {
        assert.expect(1);

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
        assert.equal(model.getters.getAutofillTooltip(), undefined);
    });

    QUnit.test(
        "Autofill content which contains pivots but which is not a pivot",
        async function (assert) {
            assert.expect(2);
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
            assert.strictEqual(
                getPivotAutofillValue(model, "F6", { direction: "bottom", steps: 1 }),
                content
            );
            assert.strictEqual(
                getPivotAutofillValue(model, "F6", { direction: "right", steps: 1 }),
                content
            );
        }
    );

    QUnit.test("Autofill pivot formula with missing pivotId", async function (assert) {
        const model = new spreadsheet.Model({
            sheets: [
                {
                    colNumber: 1,
                    rowNumber: 2,
                    cells: {
                        A1: { content: '=ODOO.PIVOT("1","bar","date","05/2023")' },
                        B1: { content: '=ODOO.PIVOT.HEADER("1","date","05/2023")' },
                    },
                },
            ],
        });
        assert.strictEqual(
            getPivotAutofillValue(model, "A1", { direction: "bottom", steps: 1 }),
            '=ODOO.PIVOT("1","bar","date","05/2023")'
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "B1", { direction: "bottom", steps: 1 }),
            '=ODOO.PIVOT.HEADER("1","date","05/2023")'
        );
        assert.deepEqual(model.getters.getTooltipFormula(getCellFormula(model, "A1"), false), [
            {
                title: "Missing pivot",
                value: "Missing pivot #1",
            },
        ]);
        assert.deepEqual(model.getters.getTooltipFormula(getCellFormula(model, "B1"), false), [
            {
                title: "Missing pivot",
                value: "Missing pivot #1",
            },
        ]);
    });

    QUnit.test("Can autofill col headers horizontally", async (assert) => {
        const { model } = await createSpreadsheetWithPivot({
            arch: /*xml*/ `
                <pivot>
                    <field name="tag_ids" type="col"/>
                    <field name="date" interval="year" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
        });
        selectCell(model, "B1");
        model.dispatch("AUTOFILL_SELECT", { col: 2, row: 0 });
        let tooltipContent;
        tooltipContent = model.getters.getAutofillTooltip().props.content;
        assert.equal(tooltipContent[tooltipContent.length - 1].value, "isCool");
        selectCell(model, "C1");
        model.dispatch("AUTOFILL_SELECT", { col: 3, row: 0 });
        tooltipContent = model.getters.getAutofillTooltip().props.content;
        assert.equal(tooltipContent[tooltipContent.length - 1].value, "Growing");
        selectCell(model, "D1");
        model.dispatch("AUTOFILL_SELECT", { col: 4, row: 0 });
        tooltipContent = model.getters.getAutofillTooltip().props.content;
        assert.equal(tooltipContent[tooltipContent.length - 1].value, "Total");
        selectCell(model, "E1");
        model.dispatch("AUTOFILL_SELECT", { col: 5, row: 0 });
        tooltipContent = model.getters.getAutofillTooltip().props.content;
        assert.equal(tooltipContent[tooltipContent.length - 1].value, "None");
    });

    QUnit.test("Can autofill col headers vertically", async (assert) => {
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
        assert.equal(tooltipContent[tooltipContent.length - 1].value, "Probability");
        model.dispatch("AUTOFILL_SELECT", { col: 1, row: 2 });
        tooltipContent = model.getters.getAutofillTooltip().props.content;
        assert.equal(tooltipContent[tooltipContent.length - 1].value, "2016");
        selectCell(model, "C1");
        model.dispatch("AUTOFILL_SELECT", { col: 2, row: 1 });
        tooltipContent = model.getters.getAutofillTooltip().props.content;
        assert.equal(tooltipContent[tooltipContent.length - 1].value, "Probability");
        model.dispatch("AUTOFILL_SELECT", { col: 2, row: 2 });
        tooltipContent = model.getters.getAutofillTooltip().props.content;
        assert.equal(tooltipContent[tooltipContent.length - 1].value, "2016");
        selectCell(model, "D1");
        model.dispatch("AUTOFILL_SELECT", { col: 3, row: 1 });
        tooltipContent = model.getters.getAutofillTooltip().props.content;
        assert.equal(tooltipContent[tooltipContent.length - 1].value, "Probability");
        model.dispatch("AUTOFILL_SELECT", { col: 3, row: 2 });
        tooltipContent = model.getters.getAutofillTooltip().props.content;
        assert.equal(tooltipContent[tooltipContent.length - 1].value, "2016");
        selectCell(model, "E1");
        model.dispatch("AUTOFILL_SELECT", { col: 4, row: 1 });
        tooltipContent = model.getters.getAutofillTooltip().props.content;
        assert.equal(tooltipContent[tooltipContent.length - 1].value, "Probability");
        model.dispatch("AUTOFILL_SELECT", { col: 4, row: 2 });
        tooltipContent = model.getters.getAutofillTooltip().props.content;
        assert.equal(tooltipContent[tooltipContent.length - 1].value, "2016");
        model.dispatch("AUTOFILL_SELECT", { col: 4, row: 3 });
        tooltipContent = model.getters.getAutofillTooltip().props.content;
        assert.equal(tooltipContent[tooltipContent.length - 1].value, "Total");
    });

    QUnit.test("Can autofill row headers horizontally", async (assert) => {
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
        model.dispatch("AUTOFILL_SELECT", { col: 1, row: 2 });
        tooltipContent = model.getters.getAutofillTooltip().props.content;
        assert.equal(tooltipContent[tooltipContent.length - 1].value, "None");
        selectCell(model, "A4");
        model.dispatch("AUTOFILL_SELECT", { col: 2, row: 3 });
        tooltipContent = model.getters.getAutofillTooltip().props.content;
        assert.equal(tooltipContent[tooltipContent.length - 1].value, "isCool");
        selectCell(model, "A5");
        model.dispatch("AUTOFILL_SELECT", { col: 1, row: 4 });
        tooltipContent = model.getters.getAutofillTooltip().props.content;
        assert.equal(tooltipContent[tooltipContent.length - 1].value, "None");
        selectCell(model, "A6");
        model.dispatch("AUTOFILL_SELECT", { col: 3, row: 5 });
        tooltipContent = model.getters.getAutofillTooltip().props.content;
        assert.equal(tooltipContent[tooltipContent.length - 1].value, "Growing");
        selectCell(model, "A7");
        model.dispatch("AUTOFILL_SELECT", { col: 1, row: 6 });
        tooltipContent = model.getters.getAutofillTooltip().props.content;
        assert.equal(tooltipContent[tooltipContent.length - 1].value, "None");
        selectCell(model, "A8");
        model.dispatch("AUTOFILL_SELECT", { col: 4, row: 7 });
        tooltipContent = model.getters.getAutofillTooltip().props.content;
        assert.equal(tooltipContent[tooltipContent.length - 1].value, "Total");
        selectCell(model, "A9");
        model.dispatch("AUTOFILL_SELECT", { col: 1, row: 8 });
        tooltipContent = model.getters.getAutofillTooltip().props.content;
        assert.equal(tooltipContent[tooltipContent.length - 1].value, "None");
    });

    QUnit.test("Can autofill row headers vertically", async (assert) => {
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
        assert.equal(tooltipContent[tooltipContent.length - 1].value, "xphone");
        selectCell(model, "A4");
        model.dispatch("AUTOFILL_SELECT", { col: 0, row: 4 });
        tooltipContent = model.getters.getAutofillTooltip().props.content;
        assert.equal(tooltipContent[tooltipContent.length - 1].value, "October 2016");
        selectCell(model, "A5");
        model.dispatch("AUTOFILL_SELECT", { col: 0, row: 5 });
        tooltipContent = model.getters.getAutofillTooltip().props.content;
        assert.equal(tooltipContent[tooltipContent.length - 1].value, "xpad");
        selectCell(model, "A6");
        model.dispatch("AUTOFILL_SELECT", { col: 0, row: 6 });
        tooltipContent = model.getters.getAutofillTooltip().props.content;
        assert.equal(tooltipContent[tooltipContent.length - 1].value, "December 2016");
        selectCell(model, "A7");
        model.dispatch("AUTOFILL_SELECT", { col: 0, row: 7 });
        tooltipContent = model.getters.getAutofillTooltip().props.content;
        assert.equal(tooltipContent[tooltipContent.length - 1].value, "xpad");
        selectCell(model, "A8");
        model.dispatch("AUTOFILL_SELECT", { col: 0, row: 8 });
        tooltipContent = model.getters.getAutofillTooltip().props.content;
        assert.equal(tooltipContent[tooltipContent.length - 1].value, "Total");
        selectCell(model, "A9");
        model.dispatch("AUTOFILL_SELECT", { col: 0, row: 9 });
        tooltipContent = model.getters.getAutofillTooltip().props.content;
        assert.equal(tooltipContent[tooltipContent.length - 1].value, "Probability");
    });

    QUnit.test("Autofill pivot keeps format but neither style nor border", async function (assert) {
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
        assert.deepEqual(startingCell.style, style);
        assert.deepEqual(model.getters.getCellBorder({ sheetId, col, row }).left, border.left);
        assert.equal(startingCell.format, "#,##0.0");

        // Check that the format of E3 has been correctly applied to E4 but not the style nor the border
        const filledCell = getCell(model, "E4");
        assert.equal(filledCell.style, undefined);
        assert.equal(model.getters.getCellBorder({ sheetId, col, row: row + 1 }), null);
        assert.equal(filledCell.format, "#,##0.0");
    });
});
