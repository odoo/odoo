import { describe, expect, test } from "@odoo/hoot";
import { registries } from "@odoo/o-spreadsheet";
import { createSpreadsheetWithChart } from "@spreadsheet/../tests/helpers/chart";
import {
    addGlobalFilter,
    setCellContent,
    setCellFormat,
    setCellStyle,
    setGlobalFilterValue,
} from "@spreadsheet/../tests/helpers/commands";
import { defineSpreadsheetModels } from "@spreadsheet/../tests/helpers/data";
import { getCell, getEvaluatedCell } from "@spreadsheet/../tests/helpers/getters";
import { THIS_YEAR_GLOBAL_FILTER } from "@spreadsheet/../tests/helpers/global_filter";
import { createModelWithDataSource } from "@spreadsheet/../tests/helpers/model";
import { createSpreadsheetWithPivot } from "@spreadsheet/../tests/helpers/pivot";
import { freezeOdooData } from "@spreadsheet/helpers/model";
import { OdooPivot, OdooPivotRuntimeDefinition } from "@spreadsheet/pivot/odoo_pivot";

const { pivotRegistry } = registries;

import { getMenuServerData } from "@spreadsheet/../tests/links/menu_data_utils";
import { createSpreadsheetWithList } from "../helpers/list";

describe.current.tags("headless");
defineSpreadsheetModels();

test("odoo pivot functions are replaced with their value", async function () {
    const { model } = await createSpreadsheetWithPivot();
    expect(getCell(model, "A3").content).toBe('=PIVOT.HEADER(1,"bar",FALSE)');
    expect(getCell(model, "C3").content).toBe(
        '=PIVOT.VALUE(1,"probability:avg","bar",FALSE,"foo",2)'
    );
    expect(getEvaluatedCell(model, "A3").value).toBe("No");
    expect(getEvaluatedCell(model, "C3").value).toBe(15);
    const data = await freezeOdooData(model);
    const cells = data.sheets[0].cells;
    expect(cells.A3.content).toBe("No", { message: "the content is replaced with the value" });
    expect(cells.C3.content).toBe("15", { message: "the content is replaced with the value" });
    expect(data.formats[cells.C3.format]).toBe("#,##0.00");
});

test("Pivot with a type different of ODOO is not converted", async function () {
    // Add a pivot with a type different of ODOO
    pivotRegistry.add("NEW_KIND_OF_PIVOT", {
        ui: OdooPivot,
        definition: OdooPivotRuntimeDefinition,
        externalData: true,
        onIterationEndEvaluation: () => {},
        granularities: [],
        isMeasureCandidate: () => false,
        isGroupable: () => false,
    });
    const spreadsheetData = {
        pivots: {
            1: {
                type: "NEW_KIND_OF_PIVOT",
                name: "Name",
                model: "partner",
                measures: ["probability"],
                formulaId: "1",
                colGroupBys: ["foo"],
                rowGroupBys: ["bar"],
                sortedColumn: null,
            },
        },
    };
    const model = await createModelWithDataSource({ spreadsheetData });
    setCellContent(model, "A1", `=PIVOT.VALUE(1, "probability:avg")`);
    setCellContent(model, "A2", `=PIVOT.HEADER(1, "measure", "probability:avg")`);
    const data = await freezeOdooData(model);
    const cells = data.sheets[0].cells;
    expect(cells.A1.content).toBe(`=PIVOT.VALUE(1, "probability:avg")`, {
        message: "the content is not replaced with the value",
    });
    expect(cells.A2.content).toBe(`=PIVOT.HEADER(1, "measure", "probability:avg")`, {
        message: "the content is not replaced with the value",
    });
});

test("values are not exported formatted", async function () {
    const { model } = await createSpreadsheetWithPivot();
    expect(getCell(model, "A3").content).toBe('=PIVOT.HEADER(1,"bar",FALSE)');
    expect(getCell(model, "C3").content).toBe(
        '=PIVOT.VALUE(1,"probability:avg","bar",FALSE,"foo",2)'
    );
    setCellFormat(model, "C3", "mmmm yyyy");
    setCellContent(model, "C4", "=C3+31");
    expect(getEvaluatedCell(model, "C3").value).toBe(15);
    expect(getEvaluatedCell(model, "C3").formattedValue).toBe("January 1900");
    expect(getEvaluatedCell(model, "C4").value).toBe(46);
    expect(getEvaluatedCell(model, "C4").formattedValue).toBe("February 1900");
    const data = await freezeOdooData(model);
    const sharedModel = await createModelWithDataSource({ spreadsheetData: data });
    expect(getEvaluatedCell(sharedModel, "C3").value).toBe(15);
    expect(getEvaluatedCell(sharedModel, "C3").formattedValue).toBe("January 1900");
    expect(getEvaluatedCell(sharedModel, "C4").value).toBe(46);
    expect(getEvaluatedCell(sharedModel, "C4").formattedValue).toBe("February 1900");
});

test("invalid expression with pivot function", async function () {
    const { model } = await createSpreadsheetWithPivot();
    setCellContent(model, "A1", "=PIVOT.VALUE(1)+"); // invalid expression
    expect(getEvaluatedCell(model, "A1").value).toBe("#BAD_EXPR");
    const data = await freezeOdooData(model);
    const cells = data.sheets[0].cells;
    expect(cells.A1.content).toBe("=PIVOT.VALUE(1)+", {
        message: "the content is left as is when the expression is invalid",
    });
});

test("odoo pivot functions detection is not case sensitive", async function () {
    const { model } = await createSpreadsheetWithPivot();
    setCellContent(model, "A1", '=pivot.value(1,"probability:avg")');
    const data = await freezeOdooData(model);
    const A1 = data.sheets[0].cells.A1;
    expect(A1.content).toBe("131", { message: "the content is replaced with the value" });
});

test("computed format is exported", async function () {
    const { model } = await createSpreadsheetWithPivot({
        arch: /* xml */ `
              <pivot>
                  <field name="pognon" type="measure"/>
              </pivot>
            `,
    });
    setCellContent(model, "A1", '=PIVOT.VALUE(1,"pognon:avg")');
    expect(getCell(model, "A1").format).toBe(undefined);
    expect(getEvaluatedCell(model, "A1").format).toBe("#,##0.00[$€]");
    const data = await freezeOdooData(model);
    const A1 = data.sheets[0].cells.A1;
    const format = data.formats[A1.format];
    expect(format).toBe("#,##0.00[$€]");
});

test("odoo charts are replaced with an image", async function () {
    const { model } = await createSpreadsheetWithChart({ type: "odoo_bar" });
    const data = await freezeOdooData(model);
    expect(data.sheets[0].figures.length).toBe(1);
    expect(data.sheets[0].figures[0].tag).toBe("image");
});

test("translation function are replaced with their value", async function () {
    const model = await createModelWithDataSource();
    setCellContent(model, "A1", `=_t("example")`);
    setCellContent(model, "A2", `=CONCATENATE("for",_t(" example"))`);
    expect(getEvaluatedCell(model, "A1").value).toBe("example");
    expect(getEvaluatedCell(model, "A2").value).toBe("for example");
    const data = await freezeOdooData(model);
    const cells = data.sheets[0].cells;
    expect(cells.A1.content).toBe("example", {
        message: "the content is replaced with the value",
    });
    expect(cells.A2.content).toBe("for example", {
        message: "the content is replaced with the value even when translation function is nested",
    });
});

test("a new sheet is added for global filters", async function () {
    const model = await createModelWithDataSource();
    await addGlobalFilter(model, THIS_YEAR_GLOBAL_FILTER);
    const data = await freezeOdooData(model);
    expect(data.sheets.length).toBe(2);
    expect(data.sheets[1].name).toBe("Active Filters");
    expect(data.sheets[1].cells.A2.content).toBe("This Year");
});

test("global filters and their display value are exported", async function () {
    const model = await createModelWithDataSource();
    await addGlobalFilter(model, THIS_YEAR_GLOBAL_FILTER);
    const data = await freezeOdooData(model);
    expect(data.globalFilters.length).toBe(1);
    expect(data.globalFilters[0].label).toBe("This Year");
    expect(data.globalFilters[0].value).toBe(new Date().getFullYear().toString());
});

test("from/to global filters are exported", async function () {
    const model = await createModelWithDataSource();
    await addGlobalFilter(model, {
        id: "42",
        type: "date",
        label: "Date Filter",
        rangeType: "from_to",
    });
    await setGlobalFilterValue(model, {
        id: "42",
        value: {
            from: "2020-01-01",
            to: "2021-01-01",
        },
    });
    const data = await freezeOdooData(model);
    const filterSheet = data.sheets[1];
    expect(filterSheet.cells.B2.content).toBe("43831");
    expect(filterSheet.cells.C2.content).toBe("44197");
    expect(filterSheet.cells.B2.format).toBe(1);
    expect(filterSheet.cells.C2.format).toBe(1);
    expect(data.formats[1]).toBe("m/d/yyyy");
    expect(data.globalFilters.length).toBe(1);
    expect(data.globalFilters[0].label).toBe("Date Filter");
    expect(data.globalFilters[0].value).toBe("1/1/2020, 1/1/2021");
});

test("from/to global filter without value is exported", async function () {
    const model = await createModelWithDataSource();
    await addGlobalFilter(model, {
        id: "42",
        type: "date",
        label: "Date Filter",
        rangeType: "from_to",
    });
    const data = await freezeOdooData(model);
    const filterSheet = data.sheets[1];
    expect(filterSheet.cells.A2.content).toBe("Date Filter");
    expect(filterSheet.cells.B2).toEqual({ content: "", format: 1 });
    expect(filterSheet.cells.C2).toEqual({ content: "", format: 1 });
    expect(data.formats[1]).toBe("m/d/yyyy");
    expect(data.globalFilters.length).toBe(1);
    expect(data.globalFilters[0].label).toBe("Date Filter");
    expect(data.globalFilters[0].value).toBe("");
});

test("odoo links are replaced with their label", async function () {
    const view = {
        name: "an odoo view",
        viewType: "list",
        action: {
            modelName: "partner",
            views: [[false, "list"]],
        },
    };
    const data = {
        sheets: [
            {
                cells: {
                    A1: { content: "[menu_xml](odoo://ir_menu_xml_id/test_menu)" },
                    A2: { content: "[menu_id](odoo://ir_menu_id/12)" },
                    A3: { content: `[odoo_view](odoo://view/${JSON.stringify(view)})` },
                    A4: { content: "[external_link](https://odoo.com)" },
                    A5: { content: "[internal_link](o-spreadsheet://Sheet1)" },
                },
            },
        ],
    };

    const model = await createModelWithDataSource({
        spreadsheetData: data,
        serverData: getMenuServerData(),
    });
    const frozenData = await freezeOdooData(model);
    expect(frozenData.sheets[0].cells.A1.content).toBe("menu_xml");
    expect(frozenData.sheets[0].cells.A2.content).toBe("menu_id");
    expect(frozenData.sheets[0].cells.A3.content).toBe("odoo_view");
    expect(frozenData.sheets[0].cells.A4.content).toBe("[external_link](https://odoo.com)");
    expect(frozenData.sheets[0].cells.A5.content).toBe("[internal_link](o-spreadsheet://Sheet1)");
});

test("spilled pivot table", async function () {
    const { model } = await createSpreadsheetWithPivot({
        arch: /* xml */ `
          <pivot>
              <field name="probability" type="measure"/>
          </pivot>
        `,
    });
    setCellContent(model, "A10", "=PIVOT(1)");
    setCellStyle(model, "B12", { bold: true });
    const data = await freezeOdooData(model);
    const sheet = data.sheets[0];
    const cells = sheet.cells;
    expect(cells.A10.content).toBe("(#1) Partner Pivot");
    expect(cells.A11.content).toBe("");
    expect(cells.A12.content).toBe("Total");
    expect(cells.B10.content).toBe("Total");
    expect(cells.B11.content).toBe("Probability");
    expect(cells.B12.content).toBe("131");
    expect(data.formats[cells.B12.format]).toBe("#,##0.00");
    expect(data.pivots).toEqual({});
    expect(sheet.styles).toEqual({ B12: 1 });
    expect(data.styles[sheet.styles["B12"]]).toEqual(
        { bold: true },
        { message: "style is preserved" }
    );
});

test("Lists are purged from the frozen data", async function () {
    const { model } = await createSpreadsheetWithList();
    const data = await freezeOdooData(model);
    expect(data.lists).toEqual({});
});
