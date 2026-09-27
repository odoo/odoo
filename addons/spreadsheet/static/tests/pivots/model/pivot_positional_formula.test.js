import { describe, expect, test } from "@odoo/hoot";
import {
    defineSpreadsheetActions,
    defineSpreadsheetModels,
} from "@spreadsheet/../tests/helpers/data";

import { setCellContent, updatePivot } from "@spreadsheet/../tests/helpers/commands";
import { getCellValue, getEvaluatedCell } from "@spreadsheet/../tests/helpers/getters";
import { createSpreadsheetWithPivot } from "@spreadsheet/../tests/helpers/pivot";
import { createModelWithDataSource } from "@spreadsheet/../tests/helpers/model";
import { waitForDataLoaded } from "@spreadsheet/helpers/model";

describe.current.tags("headless");
defineSpreadsheetModels();
defineSpreadsheetActions();

test("Can have positional args in pivot formula", async function () {
    const { model } = await createSpreadsheetWithPivot();

    // Columns
    setCellContent(model, "H1", `=PIVOT.VALUE(1,"probability:avg","#foo", 1)`);
    setCellContent(model, "H2", `=PIVOT.VALUE(1,"probability:avg","#foo", 2)`);
    setCellContent(model, "H3", `=PIVOT.VALUE(1,"probability:avg","#foo", 3)`);
    setCellContent(model, "H4", `=PIVOT.VALUE(1,"probability:avg","#foo", 4)`);
    setCellContent(model, "H5", `=PIVOT.VALUE(1,"probability:avg","#foo", 5)`);
    expect(getCellValue(model, "H1")).toBe(11);
    expect(getCellValue(model, "H2")).toBe(15);
    expect(getCellValue(model, "H3")).toBe(10);
    expect(getCellValue(model, "H4")).toBe(95);
    expect(getCellValue(model, "H5")).toBe("");

    // Rows
    setCellContent(model, "I1", `=PIVOT.VALUE(1,"probability:avg","#bar", 1)`);
    setCellContent(model, "I2", `=PIVOT.VALUE(1,"probability:avg","#bar", 2)`);
    setCellContent(model, "I3", `=PIVOT.VALUE(1,"probability:avg","#bar", 3)`);
    expect(getCellValue(model, "I1")).toBe(15);
    expect(getCellValue(model, "I2")).toBe(116);
    expect(getCellValue(model, "I3")).toBe("");
});

test("Can have positional args in pivot headers formula", async function () {
    const { model } = await createSpreadsheetWithPivot();
    // Columns
    setCellContent(model, "H1", `=PIVOT.HEADER(1,"#foo",1)`);
    setCellContent(model, "H2", `=PIVOT.HEADER(1,"#foo",2)`);
    setCellContent(model, "H3", `=PIVOT.HEADER(1,"#foo",3)`);
    setCellContent(model, "H4", `=PIVOT.HEADER(1,"#foo",4)`);
    setCellContent(model, "H5", `=PIVOT.HEADER(1,"#foo",5)`);
    setCellContent(model, "H6", `=PIVOT.HEADER(1,"#foo",5, "measure", "probability:avg")`);
    expect(getCellValue(model, "H1")).toBe(1);
    expect(getCellValue(model, "H2")).toBe(2);
    expect(getCellValue(model, "H3")).toBe(12);
    expect(getCellValue(model, "H4")).toBe(17);
    expect(getCellValue(model, "H5")).toBe("");
    expect(getCellValue(model, "H6")).toBe("Probability");

    // Rows
    setCellContent(model, "I1", `=PIVOT.HEADER(1,"#bar",1)`);
    setCellContent(model, "I2", `=PIVOT.HEADER(1,"#bar",2)`);
    setCellContent(model, "I3", `=PIVOT.HEADER(1,"#bar",3)`);
    setCellContent(model, "I4", `=PIVOT.HEADER(1,"#bar",3, "measure", "probability:avg")`);
    expect(getCellValue(model, "I1")).toBe("No");
    expect(getCellValue(model, "I2")).toBe("Yes");
    expect(getCellValue(model, "I3")).toBe("");
    expect(getCellValue(model, "I4")).toBe("Probability");
});

test("pivot positional with two levels of group bys in rows", async () => {
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
    setCellContent(model, "H1", `=PIVOT.HEADER(1,"bar","false","#product_id",1)`);
    setCellContent(model, "H2", `=PIVOT.HEADER(1,"bar","true","#product_id",1)`);
    setCellContent(model, "H3", `=PIVOT.HEADER(1,"#bar",1,"#product_id",1)`);
    setCellContent(model, "H4", `=PIVOT.HEADER(1,"#bar",2,"#product_id",1)`);
    setCellContent(model, "H5", `=PIVOT.HEADER(1,"#bar",3,"#product_id",1)`);
    expect(getCellValue(model, "H1")).toBe("xpad");
    expect(getCellValue(model, "H2")).toBe("xphone");
    expect(getCellValue(model, "H3")).toBe("xpad");
    expect(getCellValue(model, "H4")).toBe("xphone");
    expect(getCellValue(model, "H5")).toBe("");

    // Cells
    setCellContent(
        model,
        "H1",
        `=PIVOT.VALUE(1,"probability:avg","#bar",1,"#product_id",1,"#foo",2)`
    );
    setCellContent(
        model,
        "H2",
        `=PIVOT.VALUE(1,"probability:avg","#bar",1,"#product_id",2,"#foo",2)`
    );
    expect(getCellValue(model, "H1")).toBe(15);
    expect(getCellValue(model, "H2")).toBe("");
});

test("Positional argument without a number should crash", async () => {
    const { model } = await createSpreadsheetWithPivot();
    setCellContent(model, "A10", `=PIVOT.HEADER(1,"#bar","this is not a number")`);
    expect(getCellValue(model, "A10")).toBe("#ERROR");
    expect(getEvaluatedCell(model, "A10").message).toBe(
        "The function PIVOT.HEADER expects a number value, but 'this is not a number' is a string, and cannot be coerced to a number."
    );
});

test("sort first pivot column (ascending)", async () => {
    const spreadsheetData = {
        pivots: {
            1: {
                type: "ODOO",
                columns: [{ fieldName: "foo" }],
                rows: [{ fieldName: "bar" }],
                domain: [],
                measures: [{ id: "probability:sum", fieldName: "probability", aggregator: "sum" }],
                model: "partner",
                sortedColumn: {
                    domain: [{ field: "foo", type: "integer", value: 1 }],
                    measure: "probability:sum",
                    order: "asc",
                },
            },
        },
    };
    const { model } = await createModelWithDataSource({ spreadsheetData });
    setCellContent(model, "A1", `=PIVOT.HEADER(1,"#bar",1)`);
    setCellContent(model, "A2", `=PIVOT.HEADER(1,"#bar",2)`);
    setCellContent(model, "B1", `=PIVOT.VALUE(1,"probability:sum","#bar",1,"#foo",1)`);
    setCellContent(model, "B2", `=PIVOT.VALUE(1,"probability:sum","#bar",2,"#foo",1)`);
    setCellContent(model, "C1", `=PIVOT.VALUE(1,"probability:sum","#bar",1,"#foo",2)`);
    setCellContent(model, "C2", `=PIVOT.VALUE(1,"probability:sum","#bar",2,"#foo",2)`);
    setCellContent(model, "D1", `=PIVOT.VALUE(1,"probability:sum","#bar",1)`);
    setCellContent(model, "D2", `=PIVOT.VALUE(1,"probability:sum","#bar",2)`);
    await waitForDataLoaded(model);
    expect(getCellValue(model, "A1")).toBe("No");
    expect(getCellValue(model, "A2")).toBe("Yes");
    expect(getCellValue(model, "B1")).toBe("");
    expect(getCellValue(model, "B2")).toBe(11);
    expect(getCellValue(model, "C1")).toBe(15);
    expect(getCellValue(model, "C2")).toBe("");
    expect(getCellValue(model, "D1")).toBe(15);
    expect(getCellValue(model, "D2")).toBe(116);
});

test("sort first pivot column (descending)", async () => {
    const spreadsheetData = {
        pivots: {
            1: {
                type: "ODOO",
                columns: [{ fieldName: "foo" }],
                rows: [{ fieldName: "bar" }],
                domain: [],
                measures: [{ id: "probability:sum", fieldName: "probability", aggregator: "sum" }],
                model: "partner",
                sortedColumn: {
                    domain: [{ field: "foo", type: "integer", value: 1 }],
                    measure: "probability:sum",
                    order: "desc",
                },
            },
        },
    };
    const { model } = await createModelWithDataSource({ spreadsheetData });
    setCellContent(model, "A1", `=PIVOT.HEADER(1,"#bar",1)`);
    setCellContent(model, "A2", `=PIVOT.HEADER(1,"#bar",2)`);
    setCellContent(model, "B1", `=PIVOT.VALUE(1,"probability:sum","#bar",1,"#foo",1)`);
    setCellContent(model, "B2", `=PIVOT.VALUE(1,"probability:sum","#bar",2,"#foo",1)`);
    setCellContent(model, "C1", `=PIVOT.VALUE(1,"probability:sum","#bar",1,"#foo",2)`);
    setCellContent(model, "C2", `=PIVOT.VALUE(1,"probability:sum","#bar",2,"#foo",2)`);
    setCellContent(model, "D1", `=PIVOT.VALUE(1,"probability:sum","#bar",1)`);
    setCellContent(model, "D2", `=PIVOT.VALUE(1,"probability:sum","#bar",2)`);
    await waitForDataLoaded(model);
    expect(getCellValue(model, "A1")).toBe("Yes");
    expect(getCellValue(model, "A2")).toBe("No");
    expect(getCellValue(model, "B1")).toBe(11);
    expect(getCellValue(model, "B2")).toBe("");
    expect(getCellValue(model, "C1")).toBe("");
    expect(getCellValue(model, "C2")).toBe(15);
    expect(getCellValue(model, "D1")).toBe(116);
    expect(getCellValue(model, "D2")).toBe(15);
});

test("sort second pivot column (ascending)", async () => {
    const spreadsheetData = {
        pivots: {
            1: {
                type: "ODOO",
                columns: [{ fieldName: "foo" }],
                domain: [],
                measures: [{ id: "probability:sum", fieldName: "probability", aggregator: "sum" }],
                model: "partner",
                rows: [{ fieldName: "bar" }],
                name: "Partners by Foo",
                sortedColumn: {
                    domain: [{ field: "foo", type: "integer", value: 2 }],
                    measure: "probability:sum",
                    order: "asc",
                },
            },
        },
    };
    const { model } = await createModelWithDataSource({ spreadsheetData });
    setCellContent(model, "A1", `=PIVOT.HEADER(1,"#bar",1)`);
    setCellContent(model, "A2", `=PIVOT.HEADER(1,"#bar",2)`);
    setCellContent(model, "B1", `=PIVOT.VALUE(1,"probability:sum","#bar",1,"#foo",1)`);
    setCellContent(model, "B2", `=PIVOT.VALUE(1,"probability:sum","#bar",2,"#foo",1)`);
    setCellContent(model, "C1", `=PIVOT.VALUE(1,"probability:sum","#bar",1,"#foo",2)`);
    setCellContent(model, "C2", `=PIVOT.VALUE(1,"probability:sum","#bar",2,"#foo",2)`);
    setCellContent(model, "D1", `=PIVOT.VALUE(1,"probability:sum","#bar",1)`);
    setCellContent(model, "D2", `=PIVOT.VALUE(1,"probability:sum","#bar",2)`);
    await waitForDataLoaded(model);
    expect(getCellValue(model, "A1")).toBe("Yes");
    expect(getCellValue(model, "A2")).toBe("No");
    expect(getCellValue(model, "B1")).toBe(11);
    expect(getCellValue(model, "B2")).toBe("");
    expect(getCellValue(model, "C1")).toBe("");
    expect(getCellValue(model, "C2")).toBe(15);
    expect(getCellValue(model, "D1")).toBe(116);
    expect(getCellValue(model, "D2")).toBe(15);
});

test("sort second pivot column (descending)", async () => {
    const spreadsheetData = {
        pivots: {
            1: {
                type: "ODOO",
                columns: [{ fieldName: "foo" }],
                domain: [],
                measures: [{ id: "probability:sum", fieldName: "probability", aggregator: "sum" }],
                model: "partner",
                rows: [{ fieldName: "bar" }],
                name: "Partners by Foo",
                sortedColumn: {
                    domain: [{ field: "foo", type: "integer", value: 2 }],
                    measure: "probability:sum",
                    order: "desc",
                },
            },
        },
    };
    const { model } = await createModelWithDataSource({ spreadsheetData });
    setCellContent(model, "A1", `=PIVOT.HEADER(1,"#bar",1)`);
    setCellContent(model, "A2", `=PIVOT.HEADER(1,"#bar",2)`);
    setCellContent(model, "B1", `=PIVOT.VALUE(1,"probability:sum","#bar",1,"#foo",1)`);
    setCellContent(model, "B2", `=PIVOT.VALUE(1,"probability:sum","#bar",2,"#foo",1)`);
    setCellContent(model, "C1", `=PIVOT.VALUE(1,"probability:sum","#bar",1,"#foo",2)`);
    setCellContent(model, "C2", `=PIVOT.VALUE(1,"probability:sum","#bar",2,"#foo",2)`);
    setCellContent(model, "D1", `=PIVOT.VALUE(1,"probability:sum","#bar",1)`);
    setCellContent(model, "D2", `=PIVOT.VALUE(1,"probability:sum","#bar",2)`);
    await waitForDataLoaded(model);
    expect(getCellValue(model, "A1")).toBe("No");
    expect(getCellValue(model, "A2")).toBe("Yes");
    expect(getCellValue(model, "B1")).toBe("");
    expect(getCellValue(model, "B2")).toBe(11);
    expect(getCellValue(model, "C1")).toBe(15);
    expect(getCellValue(model, "C2")).toBe("");
    expect(getCellValue(model, "D1")).toBe(15);
    expect(getCellValue(model, "D2")).toBe(116);
});

test("sort second pivot measure (ascending)", async () => {
    const spreadsheetData = {
        pivots: {
            1: {
                type: "ODOO",
                rows: [{ fieldName: "product_id" }],
                columns: [],
                domain: [],
                measures: [
                    { id: "probability:sum", fieldName: "probability", aggregator: "sum" },
                    { id: "foo:sum", fieldName: "foo", aggregator: "sum" },
                ],
                model: "partner",
                sortedColumn: {
                    domain: [],
                    measure: "foo:sum",
                    order: "asc",
                },
            },
        },
    };
    const { model } = await createModelWithDataSource({ spreadsheetData });
    setCellContent(model, "A10", `=PIVOT.HEADER(1,"#product_id",1)`);
    setCellContent(model, "A11", `=PIVOT.HEADER(1,"#product_id",2)`);
    setCellContent(model, "B10", `=PIVOT.VALUE(1,"probability:sum","#product_id",1)`);
    setCellContent(model, "B11", `=PIVOT.VALUE(1,"probability:sum","#product_id",2)`);
    setCellContent(model, "C10", `=PIVOT.VALUE(1,"foo:sum","#product_id",1)`);
    setCellContent(model, "C11", `=PIVOT.VALUE(1,"foo:sum","#product_id",2)`);
    await waitForDataLoaded(model);
    expect(getCellValue(model, "A10")).toBe("xphone");
    expect(getCellValue(model, "A11")).toBe("xpad");
    expect(getCellValue(model, "B10")).toBe(10);
    expect(getCellValue(model, "B11")).toBe(121);
    expect(getCellValue(model, "C10")).toBe(12);
    expect(getCellValue(model, "C11")).toBe(20);
});

test("sort second pivot measure (descending)", async () => {
    const spreadsheetData = {
        pivots: {
            1: {
                type: "ODOO",
                columns: [],
                domain: [],
                measures: [
                    { id: "probability:sum", fieldName: "probability", aggregator: "sum" },
                    { id: "foo:sum", fieldName: "foo", aggregator: "sum" },
                ],
                model: "partner",
                rows: [{ fieldName: "product_id" }],
                sortedColumn: {
                    domain: [],
                    measure: "foo:sum",
                    order: "desc",
                },
            },
        },
    };
    const { model } = await createModelWithDataSource({ spreadsheetData });
    setCellContent(model, "A10", `=PIVOT.HEADER(1,"#product_id",1)`);
    setCellContent(model, "A11", `=PIVOT.HEADER(1,"#product_id",2)`);
    setCellContent(model, "B10", `=PIVOT.VALUE(1,"probability:sum","#product_id",1)`);
    setCellContent(model, "B11", `=PIVOT.VALUE(1,"probability:sum","#product_id",2)`);
    setCellContent(model, "C10", `=PIVOT.VALUE(1,"foo:sum","#product_id",1)`);
    setCellContent(model, "C11", `=PIVOT.VALUE(1,"foo:sum","#product_id",2)`);
    await waitForDataLoaded(model);
    expect(getCellValue(model, "A10")).toBe("xpad");
    expect(getCellValue(model, "A11")).toBe("xphone");
    expect(getCellValue(model, "B10")).toBe(121);
    expect(getCellValue(model, "B11")).toBe(10);
    expect(getCellValue(model, "C10")).toBe(20);
    expect(getCellValue(model, "C11")).toBe(12);
});

test("Formatting a pivot positional preserves the interval", async () => {
    const { model } = await createSpreadsheetWithPivot({
        arch: /*xml*/ `
                <pivot>
                    <field name="date:day" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
    });
    setCellContent(model, "A1", `=PIVOT.HEADER(1,"#date:day",1)`);
    expect(getEvaluatedCell(model, "A1").formattedValue).toBe("14 Apr 2016");
});

test("pivot positional formula with collapsed pivot", async () => {
    const { model } = await createSpreadsheetWithPivot({
        arch: /*xml*/ `
                <pivot>
                    <field name="date" interval="year" type="row"/>
                    <field name="date" interval="month" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
    });
    const pivotId = model.getters.getPivotIds()[0];
    updatePivot(model, pivotId, {
        collapsedDomains: {
            ROW: [[{ field: "date:year", value: 2016, type: "date" }]],
            COL: [],
        },
    });

    setCellContent(model, "H1", `=PIVOT.HEADER(1,"#date:year",1,"#date:month",1)`);
    expect(getEvaluatedCell(model, "H1").formattedValue).toBe("April 2016");
    setCellContent(model, "H2", `=PIVOT.HEADER(1,"#date:year",1,"#date:month",2)`);
    expect(getEvaluatedCell(model, "H2").formattedValue).toBe("October 2016");
    setCellContent(model, "H3", `=PIVOT.HEADER(1,"#date:year",1,"#date:month",3)`);
    expect(getEvaluatedCell(model, "H3").formattedValue).toBe("December 2016");
});
