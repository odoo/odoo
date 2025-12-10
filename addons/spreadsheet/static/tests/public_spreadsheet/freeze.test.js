import { animationFrame, describe, expect, test } from "@odoo/hoot";
import { registries } from "@odoo/o-spreadsheet";
import { createSpreadsheetWithChart } from "@spreadsheet/../tests/helpers/chart";
import {
    addGlobalFilter,
    setCellContent,
    setCellFormat,
    setCellStyle,
    setGlobalFilterValue,
    createCarousel,
    addChartFigureToCarousel,
} from "@spreadsheet/../tests/helpers/commands";
import { defineSpreadsheetModels } from "@spreadsheet/../tests/helpers/data";
import { getCell, getEvaluatedCell } from "@spreadsheet/../tests/helpers/getters";
import { THIS_YEAR_GLOBAL_FILTER } from "@spreadsheet/../tests/helpers/global_filter";
import { createModelWithDataSource } from "@spreadsheet/../tests/helpers/model";
import { createSpreadsheetWithPivot } from "@spreadsheet/../tests/helpers/pivot";
import { freezeOdooData, waitForDataLoaded } from "@spreadsheet/helpers/model";
import { OdooPivot, OdooPivotRuntimeDefinition } from "@spreadsheet/pivot/odoo_pivot";

const { pivotRegistry } = registries;

import { getMenuServerData } from "@spreadsheet/../tests/links/menu_data_utils";
import { createSpreadsheetWithList } from "../helpers/list";

describe.current.tags("headless");
defineSpreadsheetModels();

test("odoo pivot functions are replaced with their value", async function () {
    const { model } = await createSpreadsheetWithPivot({ pivotType: "static" });
    expect(getCell(model, "A3").content).toBe('=PIVOT.HEADER(1,"bar",FALSE)');
    expect(getCell(model, "C3").content).toBe(
        '=PIVOT.VALUE(1,"probability:avg","bar",FALSE,"foo",2)'
    );
    expect(getEvaluatedCell(model, "A3").value).toBe("No");
    expect(getEvaluatedCell(model, "C3").value).toBe(15);
    const data = await freezeOdooData(model);
    const cells = data.sheets[0].cells;
    expect(cells.A3).toBe("No", { message: "the content is replaced with the value" });
    expect(cells.C3).toBe("15", { message: "the content is replaced with the value" });
    expect(data.formats[data.sheets[0].formats.C3]).toBe("#,##0.00");
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
            },
        },
    };
    const { model } = await createModelWithDataSource({ spreadsheetData });
    setCellContent(model, "A1", `=PIVOT.VALUE(1, "probability:avg")`);
    setCellContent(model, "A2", `=PIVOT.HEADER(1, "measure", "probability:avg")`);
    const data = await freezeOdooData(model);
    const cells = data.sheets[0].cells;
    expect(cells.A1).toBe(`=PIVOT.VALUE(1, "probability:avg")`, {
        message: "the content is not replaced with the value",
    });
    expect(cells.A2).toBe(`=PIVOT.HEADER(1, "measure", "probability:avg")`, {
        message: "the content is not replaced with the value",
    });
});

test("values are not exported formatted", async function () {
    const { model } = await createSpreadsheetWithPivot({ pivotType: "static" });
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
    const { model: sharedModel } = await createModelWithDataSource({ spreadsheetData: data });
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
    expect(cells.A1).toBe("=PIVOT.VALUE(1)+", {
        message: "the content is left as is when the expression is invalid",
    });
});

test("odoo pivot functions detection is not case sensitive", async function () {
    const { model } = await createSpreadsheetWithPivot();
    setCellContent(model, "A1", '=pivot.value(1,"probability:avg")');
    const data = await freezeOdooData(model);
    const A1 = data.sheets[0].cells.A1;
    expect(A1).toBe("131", { message: "the content is replaced with the value" });
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
    await animationFrame();
    expect(getCell(model, "A1").format).toBe(undefined);
    expect(getEvaluatedCell(model, "A1").format).toBe("#,##0.00[$€]");
    const data = await freezeOdooData(model);
    const formatId = data.sheets[0].formats.A1;
    const format = data.formats[formatId];
    expect(format).toBe("#,##0.00[$€]");
    const { model: sharedModel } = await createModelWithDataSource({ spreadsheetData: data });
    expect(getCell(sharedModel, "A1").format).toBe("#,##0.00[$€]");
});

test("odoo charts are replaced with an image", async function () {
    const { model } = await createSpreadsheetWithChart({ type: "odoo_bar" });
    const data = await freezeOdooData(model);
    expect(data.sheets[0].figures.length).toBe(1);
    expect(data.sheets[0].figures[0].tag).toBe("image");
});

test("geo charts are replaced with an image", async function () {
    const { model } = await createSpreadsheetWithList({
        modelConfig: { external: { geoJsonService: { getAvailableRegions: () => [] } } },
    });
    const sheetId = model.getters.getActiveSheetId();
    model.dispatch("CREATE_CHART", {
        sheetId,
        figureId: "1",
        chartId: "chartId",
        col: 0,
        row: 0,
        offset: { x: 0, y: 0 },
        definition: {
            type: "geo",
            dataSets: [],
            dataSetsHaveTitle: false,
            title: {},
            legendPosition: "none",
        },
    });

    const data = await freezeOdooData(model);
    expect(data.sheets[0].figures.length).toBe(1);
    expect(data.sheets[0].figures[0].tag).toBe("image");
});

test("Carousels figure with odoo data is converted to an image", async function () {
    const { model } = await createSpreadsheetWithChart({ type: "odoo_bar" });
    const sheetId = model.getters.getActiveSheetId();
    const chartFigureId = model.getters.getFigures(sheetId)[0].id;
    createCarousel(model, { items: [] }, "carouselId");
    addChartFigureToCarousel(model, "carouselId", chartFigureId);

    const data = await freezeOdooData(model);
    expect(data.sheets[0].figures.length).toBe(1);
    expect(data.sheets[0].figures[0].tag).toBe("image");
});

test("translation function are replaced with their value", async function () {
    const { model } = await createModelWithDataSource();
    setCellContent(model, "A1", `=_t("example")`);
    setCellContent(model, "A2", `=CONCATENATE("for",_t(" example"))`);
    expect(getEvaluatedCell(model, "A1").value).toBe("example");
    expect(getEvaluatedCell(model, "A2").value).toBe("for example");
    const data = await freezeOdooData(model);
    const cells = data.sheets[0].cells;
    expect(cells.A1).toBe("example", {
        message: "the content is replaced with the value",
    });
    expect(cells.A2).toBe("for example", {
        message: "the content is replaced with the value even when translation function is nested",
    });
});

test("a new sheet is added for global filters", async function () {
    const { model } = await createModelWithDataSource();
    await addGlobalFilter(model, THIS_YEAR_GLOBAL_FILTER);
    const data = await freezeOdooData(model);
    expect(data.sheets.length).toBe(2);
    expect(data.sheets[1].name).toBe("Active Filters");
    expect(data.sheets[1].cells.A2).toBe("This Year");
});

test("global filters and their display value are exported", async function () {
    const { model } = await createModelWithDataSource();
    await addGlobalFilter(model, THIS_YEAR_GLOBAL_FILTER);
    const year = new Date().getFullYear().toString();
    const data = await freezeOdooData(model);
    expect(data.globalFilters.length).toBe(1);
    expect(data.globalFilters[0].label).toBe("This Year");
    expect(data.globalFilters[0].value).toBe(`1/1/${year}, 12/31/${year}`);
});

test("from/to global filters are exported", async function () {
    const { model } = await createModelWithDataSource();
    await addGlobalFilter(model, {
        id: "42",
        type: "date",
        label: "Date Filter",
    });
    await setGlobalFilterValue(model, {
        id: "42",
        value: {
            type: "range",
            from: "2020-01-01",
            to: "2021-01-01",
        },
    });
    const data = await freezeOdooData(model);
    const filterSheet = data.sheets[1];
    expect(filterSheet.cells.B2).toBe("43831");
    expect(filterSheet.cells.C2).toBe("44197");
    expect(filterSheet.formats.B2).toBe(1);
    expect(filterSheet.formats.C2).toBe(1);
    expect(data.formats[1]).toBe("m/d/yyyy");
    expect(data.globalFilters.length).toBe(1);
    expect(data.globalFilters[0].label).toBe("Date Filter");
    expect(data.globalFilters[0].value).toBe("1/1/2020, 1/1/2021");
});

test("from/to global filter without value is exported", async function () {
    const { model } = await createModelWithDataSource();
    await addGlobalFilter(model, {
        id: "42",
        type: "date",
        label: "Date Filter",
    });
    const data = await freezeOdooData(model);
    const filterSheet = data.sheets[1];
    expect(filterSheet.cells.A2).toBe("Date Filter");
    expect(filterSheet.cells.B2).toBe("");
    expect(filterSheet.cells.B2).toBe("");
    expect(filterSheet.formats.B2).toBe(1);
    expect(filterSheet.formats.C2).toBe(1);
    expect(data.formats[1]).toBe("m/d/yyyy");
    expect(data.globalFilters.length).toBe(1);
    expect(data.globalFilters[0].label).toBe("Date Filter");
    expect(data.globalFilters[0].value).toBe("");
});

test("Empty ODOO.LIST result is frozen to an empty string", async function () {
    const { model } = await createSpreadsheetWithList();
    setCellContent(model, "A1", '=ODOO.LIST(1, 9999,"probability")'); // has no record
    await waitForDataLoaded(model);
    expect(getEvaluatedCell(model, "A1").value).toBe("");
    const frozenData = await freezeOdooData(model);
    expect(frozenData.sheets[0].cells.A1).toBe('=""');
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
                    A1: "[menu_xml](odoo://ir_menu_xml_id/test_menu)",
                    A2: "[menu_id](odoo://ir_menu_id/12)",
                    A3: `[odoo_view](odoo://view/${JSON.stringify(view)})`,
                    A4: "[external_link](https://odoo.com)",
                    A5: "[internal_link](o-spreadsheet://Sheet1)",
                },
            },
        ],
    };

    const { model } = await createModelWithDataSource({
        spreadsheetData: data,
        serverData: getMenuServerData(),
    });
    const frozenData = await freezeOdooData(model);
    expect(frozenData.sheets[0].cells.A1).toBe("menu_xml");
    expect(frozenData.sheets[0].cells.A2).toBe("menu_id");
    expect(frozenData.sheets[0].cells.A3).toBe("odoo_view");
    expect(frozenData.sheets[0].cells.A4).toBe("[external_link](https://odoo.com)");
    expect(frozenData.sheets[0].cells.A5).toBe("[internal_link](o-spreadsheet://Sheet1)");
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
    expect(cells.A10).toBe("Partner Pivot");
    expect(cells.A11).toBe('=""');
    expect(cells.A12).toBe("Total");
    expect(cells.B10).toBe("Total");
    expect(cells.B11).toBe("Probability");
    expect(cells.B12).toBe("131");
    expect(data.formats[sheet.formats.B12]).toBe("#,##0.00");
    expect(data.pivots).toEqual({});
    expect(sheet.styles).toEqual({ B12: 1 });
    expect(data.styles[sheet.styles["B12"]]).toEqual(
        { bold: true },
        { message: "style is preserved" }
    );
});

test("empty string computed measure is exported as =\"\"", async function () {
    const { model } = await createSpreadsheetWithPivot();
    setCellContent(model, "A10", "=PIVOT(1)");
    expect(getEvaluatedCell(model, "B12").value).toBe(""); // empty value
    const data = await freezeOdooData(model);
    const cells = data.sheets[0].cells;
    expect(cells.B12).toBe('=""');
});

test("Lists are purged from the frozen data", async function () {
    const { model } = await createSpreadsheetWithList();
    const data = await freezeOdooData(model);
    expect(data.lists).toEqual({});
});
