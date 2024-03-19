/** @odoo-module */

import { nextTick } from "@web/../tests/helpers/utils";
import { setCellContent } from "../../utils/commands";
import { getEvaluatedCell, getEvaluatedFormatGrid, getEvaluatedGrid } from "../../utils/getters";
import { createSpreadsheetWithPivot } from "../../utils/pivot";

let model;

QUnit.module("PIVOT", {
    async beforeEach(assert) {
        ({ model } = await createSpreadsheetWithPivot({
            arch: /* xml */ `
            <pivot>
                <field name="product_id" type="col"/>
                <field name="foo" type="row"/>
                <field name="probability" type="measure"/>
            </pivot>`,
        }));
        model.dispatch("CREATE_SHEET", { sheetId: "42" });
    },
});

QUnit.test("full PIVOT() values", async function (assert) {
    setCellContent(model, "A1", `=PIVOT("1")`, "42");
    // prettier-ignore
    assert.deepEqual(getEvaluatedGrid(model, "A1:D7", "42"), [
        ["(#1) Partner Pivot",    "xphone",       "xpad",         "Total"],
        ["",            "Probability",  "Probability",  "Probability"],
        [1,             "",             11,             11],
        [2,             "",             15,             15],
        [12,            10,             "",             10],
        [17,            "",             95,             95],
        ["Total",       10,             121,            131],
    ]);
});

QUnit.test("full PIVOT() formats", async function (assert) {
    setCellContent(model, "A1", `=PIVOT("1")`, "42");
    // prettier-ignore
    assert.deepEqual(getEvaluatedFormatGrid(model, "A1:D7", "42"), [
        [undefined, undefined,  undefined,  undefined],
        [undefined, undefined,  undefined,  undefined],
        ["0",       "#,##0.00", "#,##0.00", "#,##0.00"],
        ["0",       "#,##0.00", "#,##0.00", "#,##0.00"],
        ["0",       "#,##0.00", "#,##0.00", "#,##0.00"],
        ["0",       "#,##0.00", "#,##0.00", "#,##0.00"],
        [undefined, "#,##0.00", "#,##0.00", "#,##0.00"],
    ]);
});

QUnit.test("PIVOT(row_count=1)", async function (assert) {
    setCellContent(model, "A1", `=PIVOT("1", 1)`, "42");
    // prettier-ignore
    assert.deepEqual(getEvaluatedGrid(model, "A1:D4", "42"), [
        ["(#1) Partner Pivot",  "xphone",       "xpad",         "Total"],
        ["",                    "Probability",  "Probability",  "Probability"],
        [1,                     "",             11,             11],
        [null,                  null,           null,           null],
    ]);
});

QUnit.test("PIVOT(row_count=0)", async function (assert) {
    setCellContent(model, "A1", `=PIVOT("1", 0)`, "42");
    // prettier-ignore
    assert.deepEqual(getEvaluatedGrid(model, "A1:D3", "42"), [
        ["(#1) Partner Pivot",  "xphone",       "xpad",         "Total"],
        ["",                    "Probability",  "Probability",  "Probability"],
        [null,                  null,           null,           null],
    ]);
});

QUnit.test("PIVOT(negative row_count)", async function (assert) {
    setCellContent(model, "A1", `=PIVOT("1", -1)`, "42");
    assert.strictEqual(getEvaluatedCell(model, "A1", "42").value, "#ERROR");
    assert.strictEqual(
        getEvaluatedCell(model, "A1", "42").message,
        "The number of rows must be positive."
    );
});

QUnit.test("PIVOT(include_column_titles=FALSE)", async function (assert) {
    setCellContent(model, "A1", `=PIVOT("1",,,FALSE)`, "42");
    // prettier-ignore
    assert.deepEqual(getEvaluatedGrid(model, "A1:D5", "42"), [
        [1,         "",             11,             11],
        [2,         "",             15,             15],
        [12,        10,             "",             10],
        [17,        "",             95,             95],
        ["Total",   10,             121,            131],
    ]);
});

QUnit.test("PIVOT(include_total=FALSE) with no groupbys applied", async function (assert) {
    const { model } = await createSpreadsheetWithPivot({
        arch: /* xml */ `
        <pivot>
            <field name="probability" type="measure"/>
        </pivot>`,
    });
    model.dispatch("CREATE_SHEET", { sheetId: "42" });
    setCellContent(model, "A1", `=PIVOT("1",,FALSE)`, "42");
    // prettier-ignore
    assert.deepEqual(getEvaluatedGrid(model, "A1:B3", "42"), [
            ["(#1) Partner Pivot",  "Total"],
            ["",                    "Probability"],
            ["Total",               131],
        ]);
});

QUnit.test(
    "PIVOT(include_total=FALSE) with multiple measures and no groupbys applied",
    async function (assert) {
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
        assert.deepEqual(getEvaluatedGrid(model, "A1:C3", "42"), [
            ["(#1) Partner Pivot",  "Total",        ""],
            ["",                    "Probability",  "Foo"],
            ["Total",               131,            32],
        ]);
    }
);

QUnit.test("PIVOT(include_total=FALSE) with only row groupby applied", async function (assert) {
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
    assert.deepEqual(getEvaluatedGrid(model, "A1:C7", "42"), [
            ["(#1) Partner Pivot",  "Total",        null],
            ["",                    "Probability",  null],
            [1,                     11,             null],
            [2,                     15,             null],
            [12,                    10,             null],
            [17,                    95,             null],
            [null,                  null,           null],
        ]);
});

QUnit.test(
    "PIVOT(include_total=FALSE) with multiple measures and only row groupby applied",
    async function (assert) {
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
        assert.deepEqual(getEvaluatedGrid(model, "A1:D5", "42"), [
            ["(#1) Partner Pivot",      "Total",            "",        null],
            ["",                        "Probability",      "Foo",     null],
            ["xphone",                  10,                 12,        null],
            ["xpad",                    121,                20,        null],
            [null,                      null,               null,      null],
        ]);
    }
);

QUnit.test("PIVOT(include_total=FALSE) with only col groupby applied", async function (assert) {
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
    assert.deepEqual(getEvaluatedGrid(model, "A1:D4", "42"), [
            ["(#1) Partner Pivot",     "xphone",          "xpad",            null],
            ["",                       "Probability",     "Probability",     null],
            ["Total",                  10,                121,               null],
            [null,                     null,              null,              null],
        ]);
});

QUnit.test("PIVOT(include_total=FALSE, include_column_titles=FALSE)", async function (assert) {
    setCellContent(model, "A1", `=PIVOT("1",,FALSE,FALSE)`, "42");
    // prettier-ignore
    assert.deepEqual(getEvaluatedGrid(model, "A1:D5", "42"), [
            [1,         "",             11,             null],
            [2,         "",             15,             null],
            [12,        10,             "",             null],
            [17,        "",             95,             null],
            [null,      null,           null,           null],
        ]);
});

QUnit.test(
    "PIVOT(row_count=1, include_total=FALSE, include_column_titles=FALSE)",
    async function (assert) {
        setCellContent(model, "A1", `=PIVOT("1",1,FALSE,FALSE)`, "42");
        // prettier-ignore
        assert.deepEqual(getEvaluatedGrid(model, "A1:D2", "42"), [
            [1,         "",             11,             null],
            [null,      null,           null,           null],
        ]);
    }
);

QUnit.test(
    "PIVOT(row_count=0, include_total=FALSE, include_column_titles=FALSE)",
    async function (assert) {
        setCellContent(model, "A1", `=PIVOT("1",0,FALSE,FALSE)`, "42");
        // prettier-ignore
        assert.deepEqual(getEvaluatedGrid(model, "A1:D1", "42"), [
            ["(#1) Partner Pivot", null, null, null],
        ]);
    }
);

QUnit.test(
    "PIVOT(row_count=0, include_total=TRUE, include_column_titles=FALSE)",
    async function (assert) {
        setCellContent(model, "A1", `=PIVOT("1",0,TRUE,FALSE)`, "42");
        // prettier-ignore
        assert.deepEqual(getEvaluatedGrid(model, "A1:D1", "42"), [
            ["(#1) Partner Pivot", null, null, null],
        ]);
    }
);

QUnit.test("PIVOT with multiple row groups", async function (assert) {
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
    assert.deepEqual(getEvaluatedGrid(model, "A1:D11", firstSheetId), [
        [null,          "xphone",       "xpad",         "Total"],
        ["Foo",         "Probability",  "Probability",  "Probability"],
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
    assert.deepEqual(getEvaluatedGrid(model, "A1:D11", "42"), [
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
    assert.deepEqual(getEvaluatedGrid(model, "A1:D11", "42"), [
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

QUnit.test("edit pivot groups", async function (assert) {
    setCellContent(model, "A1", `=PIVOT("1")`, "42");
    const originalGrid = getEvaluatedGrid(model, "A1:D7", "42");
    // prettier-ignore
    assert.deepEqual(originalGrid, [
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
            ...model.getters.getPivotDefinition(pivotId),
            columns: [],
            rows: [],
        },
    });
    await nextTick();
    // prettier-ignore
    assert.deepEqual(getEvaluatedGrid(model, "A1:B3", "42"), [
        ["(#1) Partner Pivot",  "Total"],
        ["",                    "Probability"],
        ["Total",               131],
    ]);
    model.dispatch("REQUEST_UNDO");
    await nextTick();
    assert.deepEqual(getEvaluatedGrid(model, "A1:D7", "42"), originalGrid);
});

QUnit.test("Renaming the pivot reevaluates the PIVOT function", async function (assert) {
    const pivotId = model.getters.getPivotIds()[0];
    setCellContent(model, "A1", `=PIVOT("1")`, "42");
    assert.equal(getEvaluatedCell(model, "A1", "42").value, "(#1) Partner Pivot");
    model.dispatch("RENAME_PIVOT", {
        pivotId,
        name: "New Name",
    });
    assert.equal(getEvaluatedCell(model, "A1", "42").value, "(#1) New Name");
});
