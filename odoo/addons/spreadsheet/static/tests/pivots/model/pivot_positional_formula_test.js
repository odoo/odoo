/** @odoo-module */

import { setCellContent } from "@spreadsheet/../tests/utils/commands";
import { getCellValue, getEvaluatedCell } from "@spreadsheet/../tests/utils/getters";
import { createSpreadsheetWithPivot } from "@spreadsheet/../tests/utils/pivot";
import {
    createModelWithDataSource,
    waitForDataSourcesLoaded,
} from "@spreadsheet/../tests/utils/model";

QUnit.module("spreadsheet > positional pivot formula", {}, () => {
    QUnit.test("Can have positional args in pivot formula", async function (assert) {
        const { model } = await createSpreadsheetWithPivot();

        // Columns
        setCellContent(model, "H1", `=ODOO.PIVOT(1,"probability","#foo", 1)`);
        setCellContent(model, "H2", `=ODOO.PIVOT(1,"probability","#foo", 2)`);
        setCellContent(model, "H3", `=ODOO.PIVOT(1,"probability","#foo", 3)`);
        setCellContent(model, "H4", `=ODOO.PIVOT(1,"probability","#foo", 4)`);
        setCellContent(model, "H5", `=ODOO.PIVOT(1,"probability","#foo", 5)`);
        assert.strictEqual(getCellValue(model, "H1"), 11);
        assert.strictEqual(getCellValue(model, "H2"), 15);
        assert.strictEqual(getCellValue(model, "H3"), 10);
        assert.strictEqual(getCellValue(model, "H4"), 95);
        assert.strictEqual(getCellValue(model, "H5"), "");

        // Rows
        setCellContent(model, "I1", `=ODOO.PIVOT(1,"probability","#bar", 1)`);
        setCellContent(model, "I2", `=ODOO.PIVOT(1,"probability","#bar", 2)`);
        setCellContent(model, "I3", `=ODOO.PIVOT(1,"probability","#bar", 3)`);
        assert.strictEqual(getCellValue(model, "I1"), 15);
        assert.strictEqual(getCellValue(model, "I2"), 116);
        assert.strictEqual(getCellValue(model, "I3"), "");
    });

    QUnit.test("Can have positional args in pivot headers formula", async function (assert) {
        const { model } = await createSpreadsheetWithPivot();
        // Columns
        setCellContent(model, "H1", `=ODOO.PIVOT.HEADER(1,"#foo",1)`);
        setCellContent(model, "H2", `=ODOO.PIVOT.HEADER(1,"#foo",2)`);
        setCellContent(model, "H3", `=ODOO.PIVOT.HEADER(1,"#foo",3)`);
        setCellContent(model, "H4", `=ODOO.PIVOT.HEADER(1,"#foo",4)`);
        setCellContent(model, "H5", `=ODOO.PIVOT.HEADER(1,"#foo",5)`);
        setCellContent(model, "H6", `=ODOO.PIVOT.HEADER(1,"#foo",5, "measure", "probability")`);
        assert.strictEqual(getCellValue(model, "H1"), 1);
        assert.strictEqual(getCellValue(model, "H2"), 2);
        assert.strictEqual(getCellValue(model, "H3"), 12);
        assert.strictEqual(getCellValue(model, "H4"), 17);
        assert.strictEqual(getCellValue(model, "H5"), "");
        assert.strictEqual(getCellValue(model, "H6"), "Probability");

        // Rows
        setCellContent(model, "I1", `=ODOO.PIVOT.HEADER(1,"#bar",1)`);
        setCellContent(model, "I2", `=ODOO.PIVOT.HEADER(1,"#bar",2)`);
        setCellContent(model, "I3", `=ODOO.PIVOT.HEADER(1,"#bar",3)`);
        setCellContent(model, "I4", `=ODOO.PIVOT.HEADER(1,"#bar",3, "measure", "probability")`);
        assert.strictEqual(getCellValue(model, "I1"), "No");
        assert.strictEqual(getCellValue(model, "I2"), "Yes");
        assert.strictEqual(getCellValue(model, "I3"), "");
        assert.strictEqual(getCellValue(model, "I4"), "Probability");
    });

    QUnit.test("pivot positional with two levels of group bys in rows", async (assert) => {
        const { model } = await createSpreadsheetWithPivot({
            arch: /*xml*/ `
                <pivot>
                    <field name="bar" type="row"/>
                    <field name="product_id" type="row"/>
                    <field name="foo" type="col"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
        });
        // Rows Headers
        setCellContent(model, "H1", `=ODOO.PIVOT.HEADER(1,"bar","false","#product_id",1)`);
        setCellContent(model, "H2", `=ODOO.PIVOT.HEADER(1,"bar","true","#product_id",1)`);
        setCellContent(model, "H3", `=ODOO.PIVOT.HEADER(1,"#bar",1,"#product_id",1)`);
        setCellContent(model, "H4", `=ODOO.PIVOT.HEADER(1,"#bar",2,"#product_id",1)`);
        setCellContent(model, "H5", `=ODOO.PIVOT.HEADER(1,"#bar",3,"#product_id",1)`);
        assert.strictEqual(getCellValue(model, "H1"), "xpad");
        assert.strictEqual(getCellValue(model, "H2"), "xphone");
        assert.strictEqual(getCellValue(model, "H3"), "xpad");
        assert.strictEqual(getCellValue(model, "H4"), "xphone");
        assert.strictEqual(getCellValue(model, "H5"), "");

        // Cells
        setCellContent(
            model,
            "H1",
            `=ODOO.PIVOT(1,"probability","#bar",1,"#product_id",1,"#foo",2)`
        );
        setCellContent(
            model,
            "H2",
            `=ODOO.PIVOT(1,"probability","#bar",1,"#product_id",2,"#foo",2)`
        );
        assert.strictEqual(getCellValue(model, "H1"), 15);
        assert.strictEqual(getCellValue(model, "H2"), "");
    });

    QUnit.test("Positional argument without a number should crash", async (assert) => {
        const { model } = await createSpreadsheetWithPivot();
        setCellContent(model, "A10", `=ODOO.PIVOT.HEADER(1,"#bar","this is not a number")`);
        assert.strictEqual(getCellValue(model, "A10"), "#ERROR");
        assert.strictEqual(
            getEvaluatedCell(model, "A10").error.message,
            "The function ODOO.PIVOT.HEADER expects a number value, but 'this is not a number' is a string, and cannot be coerced to a number."
        );
    });

    QUnit.test("sort first pivot column (ascending)", async (assert) => {
        const spreadsheetData = {
            pivots: {
                1: {
                    colGroupBys: ["foo"],
                    rowGroupBys: ["bar"],
                    domain: [],
                    id: "1",
                    measures: [{ field: "probability" }],
                    model: "partner",
                    sortedColumn: {
                        groupId: [[], [1]],
                        measure: "probability",
                        order: "asc",
                    },
                },
            },
        };
        const model = await createModelWithDataSource({ spreadsheetData });
        setCellContent(model, "A1", `=ODOO.PIVOT.HEADER(1,"#bar",1)`);
        setCellContent(model, "A2", `=ODOO.PIVOT.HEADER(1,"#bar",2)`);
        setCellContent(model, "B1", `=ODOO.PIVOT(1,"probability","#bar",1,"#foo",1)`);
        setCellContent(model, "B2", `=ODOO.PIVOT(1,"probability","#bar",2,"#foo",1)`);
        setCellContent(model, "C1", `=ODOO.PIVOT(1,"probability","#bar",1,"#foo",2)`);
        setCellContent(model, "C2", `=ODOO.PIVOT(1,"probability","#bar",2,"#foo",2)`);
        setCellContent(model, "D1", `=ODOO.PIVOT(1,"probability","#bar",1)`);
        setCellContent(model, "D2", `=ODOO.PIVOT(1,"probability","#bar",2)`);
        await waitForDataSourcesLoaded(model);
        assert.strictEqual(getCellValue(model, "A1"), "No");
        assert.strictEqual(getCellValue(model, "A2"), "Yes");
        assert.strictEqual(getCellValue(model, "B1"), "");
        assert.strictEqual(getCellValue(model, "B2"), 11);
        assert.strictEqual(getCellValue(model, "C1"), 15);
        assert.strictEqual(getCellValue(model, "C2"), "");
        assert.strictEqual(getCellValue(model, "D1"), 15);
        assert.strictEqual(getCellValue(model, "D2"), 116);
    });

    QUnit.test("sort first pivot column (descending)", async (assert) => {
        const spreadsheetData = {
            pivots: {
                1: {
                    colGroupBys: ["foo"],
                    rowGroupBys: ["bar"],
                    domain: [],
                    id: "1",
                    measures: [{ field: "probability" }],
                    model: "partner",
                    sortedColumn: {
                        groupId: [[], [1]],
                        measure: "probability",
                        order: "desc",
                    },
                },
            },
        };
        const model = await createModelWithDataSource({ spreadsheetData });
        setCellContent(model, "A1", `=ODOO.PIVOT.HEADER(1,"#bar",1)`);
        setCellContent(model, "A2", `=ODOO.PIVOT.HEADER(1,"#bar",2)`);
        setCellContent(model, "B1", `=ODOO.PIVOT(1,"probability","#bar",1,"#foo",1)`);
        setCellContent(model, "B2", `=ODOO.PIVOT(1,"probability","#bar",2,"#foo",1)`);
        setCellContent(model, "C1", `=ODOO.PIVOT(1,"probability","#bar",1,"#foo",2)`);
        setCellContent(model, "C2", `=ODOO.PIVOT(1,"probability","#bar",2,"#foo",2)`);
        setCellContent(model, "D1", `=ODOO.PIVOT(1,"probability","#bar",1)`);
        setCellContent(model, "D2", `=ODOO.PIVOT(1,"probability","#bar",2)`);
        await waitForDataSourcesLoaded(model);
        assert.strictEqual(getCellValue(model, "A1"), "Yes");
        assert.strictEqual(getCellValue(model, "A2"), "No");
        assert.strictEqual(getCellValue(model, "B1"), 11);
        assert.strictEqual(getCellValue(model, "B2"), "");
        assert.strictEqual(getCellValue(model, "C1"), "");
        assert.strictEqual(getCellValue(model, "C2"), 15);
        assert.strictEqual(getCellValue(model, "D1"), 116);
        assert.strictEqual(getCellValue(model, "D2"), 15);
    });

    QUnit.test("sort second pivot column (ascending)", async (assert) => {
        const spreadsheetData = {
            pivots: {
                1: {
                    colGroupBys: ["foo"],
                    domain: [],
                    id: "1",
                    measures: [{ field: "probability" }],
                    model: "partner",
                    rowGroupBys: ["bar"],
                    name: "Partners by Foo",
                    sortedColumn: {
                        groupId: [[], [2]],
                        measure: "probability",
                        order: "asc",
                    },
                },
            },
        };
        const model = await createModelWithDataSource({ spreadsheetData });
        setCellContent(model, "A1", `=ODOO.PIVOT.HEADER(1,"#bar",1)`);
        setCellContent(model, "A2", `=ODOO.PIVOT.HEADER(1,"#bar",2)`);
        setCellContent(model, "B1", `=ODOO.PIVOT(1,"probability","#bar",1,"#foo",1)`);
        setCellContent(model, "B2", `=ODOO.PIVOT(1,"probability","#bar",2,"#foo",1)`);
        setCellContent(model, "C1", `=ODOO.PIVOT(1,"probability","#bar",1,"#foo",2)`);
        setCellContent(model, "C2", `=ODOO.PIVOT(1,"probability","#bar",2,"#foo",2)`);
        setCellContent(model, "D1", `=ODOO.PIVOT(1,"probability","#bar",1)`);
        setCellContent(model, "D2", `=ODOO.PIVOT(1,"probability","#bar",2)`);
        await waitForDataSourcesLoaded(model);
        assert.strictEqual(getCellValue(model, "A1"), "Yes");
        assert.strictEqual(getCellValue(model, "A2"), "No");
        assert.strictEqual(getCellValue(model, "B1"), 11);
        assert.strictEqual(getCellValue(model, "B2"), "");
        assert.strictEqual(getCellValue(model, "C1"), "");
        assert.strictEqual(getCellValue(model, "C2"), 15);
        assert.strictEqual(getCellValue(model, "D1"), 116);
        assert.strictEqual(getCellValue(model, "D2"), 15);
    });

    QUnit.test("sort second pivot column (descending)", async (assert) => {
        const spreadsheetData = {
            pivots: {
                1: {
                    colGroupBys: ["foo"],
                    domain: [],
                    id: "1",
                    measures: [{ field: "probability" }],
                    model: "partner",
                    rowGroupBys: ["bar"],
                    name: "Partners by Foo",
                    sortedColumn: {
                        groupId: [[], [2]],
                        measure: "probability",
                        order: "desc",
                    },
                },
            },
        };
        const model = await createModelWithDataSource({ spreadsheetData });
        setCellContent(model, "A1", `=ODOO.PIVOT.HEADER(1,"#bar",1)`);
        setCellContent(model, "A2", `=ODOO.PIVOT.HEADER(1,"#bar",2)`);
        setCellContent(model, "B1", `=ODOO.PIVOT(1,"probability","#bar",1,"#foo",1)`);
        setCellContent(model, "B2", `=ODOO.PIVOT(1,"probability","#bar",2,"#foo",1)`);
        setCellContent(model, "C1", `=ODOO.PIVOT(1,"probability","#bar",1,"#foo",2)`);
        setCellContent(model, "C2", `=ODOO.PIVOT(1,"probability","#bar",2,"#foo",2)`);
        setCellContent(model, "D1", `=ODOO.PIVOT(1,"probability","#bar",1)`);
        setCellContent(model, "D2", `=ODOO.PIVOT(1,"probability","#bar",2)`);
        await waitForDataSourcesLoaded(model);
        assert.strictEqual(getCellValue(model, "A1"), "No");
        assert.strictEqual(getCellValue(model, "A2"), "Yes");
        assert.strictEqual(getCellValue(model, "B1"), "");
        assert.strictEqual(getCellValue(model, "B2"), 11);
        assert.strictEqual(getCellValue(model, "C1"), 15);
        assert.strictEqual(getCellValue(model, "C2"), "");
        assert.strictEqual(getCellValue(model, "D1"), 15);
        assert.strictEqual(getCellValue(model, "D2"), 116);
    });

    QUnit.test("sort second pivot measure (ascending)", async (assert) => {
        const spreadsheetData = {
            pivots: {
                1: {
                    rowGroupBys: ["product_id"],
                    colGroupBys: [],
                    domain: [],
                    id: "1",
                    measures: [{ field: "probability" }, { field: "foo" }],
                    model: "partner",
                    sortedColumn: {
                        groupId: [[], []],
                        measure: "foo",
                        order: "asc",
                    },
                },
            },
        };
        const model = await createModelWithDataSource({ spreadsheetData });
        setCellContent(model, "A10", `=ODOO.PIVOT.HEADER(1,"#product_id",1)`);
        setCellContent(model, "A11", `=ODOO.PIVOT.HEADER(1,"#product_id",2)`);
        setCellContent(model, "B10", `=ODOO.PIVOT(1,"probability","#product_id",1)`);
        setCellContent(model, "B11", `=ODOO.PIVOT(1,"probability","#product_id",2)`);
        setCellContent(model, "C10", `=ODOO.PIVOT(1,"foo","#product_id",1)`);
        setCellContent(model, "C11", `=ODOO.PIVOT(1,"foo","#product_id",2)`);
        await waitForDataSourcesLoaded(model);
        assert.strictEqual(getCellValue(model, "A10"), "xphone");
        assert.strictEqual(getCellValue(model, "A11"), "xpad");
        assert.strictEqual(getCellValue(model, "B10"), 10);
        assert.strictEqual(getCellValue(model, "B11"), 121);
        assert.strictEqual(getCellValue(model, "C10"), 12);
        assert.strictEqual(getCellValue(model, "C11"), 20);
    });

    QUnit.test("sort second pivot measure (descending)", async (assert) => {
        const spreadsheetData = {
            pivots: {
                1: {
                    colGroupBys: [],
                    domain: [],
                    id: "1",
                    measures: [{ field: "probability" }, { field: "foo" }],
                    model: "partner",
                    rowGroupBys: ["product_id"],
                    sortedColumn: {
                        groupId: [[], []],
                        measure: "foo",
                        order: "desc",
                    },
                },
            },
        };
        const model = await createModelWithDataSource({ spreadsheetData });
        setCellContent(model, "A10", `=ODOO.PIVOT.HEADER(1,"#product_id",1)`);
        setCellContent(model, "A11", `=ODOO.PIVOT.HEADER(1,"#product_id",2)`);
        setCellContent(model, "B10", `=ODOO.PIVOT(1,"probability","#product_id",1)`);
        setCellContent(model, "B11", `=ODOO.PIVOT(1,"probability","#product_id",2)`);
        setCellContent(model, "C10", `=ODOO.PIVOT(1,"foo","#product_id",1)`);
        setCellContent(model, "C11", `=ODOO.PIVOT(1,"foo","#product_id",2)`);
        await waitForDataSourcesLoaded(model);
        assert.strictEqual(getCellValue(model, "A10"), "xpad");
        assert.strictEqual(getCellValue(model, "A11"), "xphone");
        assert.strictEqual(getCellValue(model, "B10"), 121);
        assert.strictEqual(getCellValue(model, "B11"), 10);
        assert.strictEqual(getCellValue(model, "C10"), 20);
        assert.strictEqual(getCellValue(model, "C11"), 12);
    });

    QUnit.test("Formatting a pivot positional preserves the interval", async (assert) => {
        const { model } = await createSpreadsheetWithPivot({
            arch: /*xml*/ `
                <pivot>
                    <field name="date:day" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
        });
        setCellContent(model, "A1", `=ODOO.PIVOT.HEADER(1,"#date:day",1)`);
        assert.strictEqual(getEvaluatedCell(model, "A1").formattedValue, "4/14/2016");
    });
});
