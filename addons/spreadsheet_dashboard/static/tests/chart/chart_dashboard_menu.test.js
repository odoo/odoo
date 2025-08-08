import { describe, expect, test } from "@odoo/hoot";
import { Model } from "@odoo/o-spreadsheet";
import { insertChartInSpreadsheet } from "@spreadsheet/../tests/helpers/chart";
import { createBasicChart, createScorecardChart } from "@spreadsheet/../tests/helpers/commands";
import { makeSpreadsheetMockEnv } from "@spreadsheet/../tests/helpers/model";
import { OdooDataProvider } from "@spreadsheet/data_sources/odoo_data_provider";
import { createDashboardActionWithData } from "@spreadsheet_dashboard/../tests/helpers/dashboard_action";
import { defineSpreadsheetDashboardModels } from "@spreadsheet_dashboard/../tests/helpers/data";
import { contains } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineSpreadsheetDashboardModels();

test("Can change type of odoo chart in dashboard", async () => {
    const env = await makeSpreadsheetMockEnv();
    const setupModel = new Model({}, { custom: { odooDataProvider: new OdooDataProvider(env) } });
    insertChartInSpreadsheet(setupModel, "odoo_bar");
    const { model } = await createDashboardActionWithData(setupModel.exportData());

    expect(".o-chart-dashboard-item[data-id='odoo_bar']").toHaveClass("active");
    await contains(".o-chart-dashboard-item[data-id='odoo_line']", { visible: false }).click();

    const chartId = model.getters.getChartIds(model.getters.getActiveSheetId())[0];
    const chartDefinition = model.getters.getChartDefinition(chartId);
    expect(chartDefinition.type).toBe("odoo_line");
});

test("Can change type of spreadsheet chart in dashboard", async () => {
    const setupModel = new Model();
    createBasicChart(setupModel, "chartId");
    const { model } = await createDashboardActionWithData(setupModel.exportData());

    expect(".o-chart-dashboard-item[data-id='bar']").toHaveClass("active");

    await contains(".o-chart-dashboard-item[data-id='pie']", { visible: false }).click();

    const chartId = model.getters.getChartIds(model.getters.getActiveSheetId())[0];
    const chartDefinition = model.getters.getChartDefinition(chartId);
    expect(chartDefinition.type).toBe("pie");
});

test("Can only change type of line/pie/bar charts", async () => {
    const env = await makeSpreadsheetMockEnv();
    const setupModel = new Model({}, { custom: { odooDataProvider: new OdooDataProvider(env) } });
    insertChartInSpreadsheet(setupModel, "odoo_radar");
    createScorecardChart(setupModel, "chartId");
    await createDashboardActionWithData(setupModel.exportData());

    expect(".o-chart-dashboard-item[data-id='pie']").toHaveCount(0);
});

test("Data source of cumulative line chart isn't reloaded after type change", async () => {
    const env = await makeSpreadsheetMockEnv();
    const setupModel = new Model({}, { custom: { odooDataProvider: new OdooDataProvider(env) } });
    const chartId = insertChartInSpreadsheet(setupModel, "odoo_line", { cumulative: true });
    const { model } = await createDashboardActionWithData(setupModel.exportData());

    const dataSource = model.getters.getChartDataSource(chartId);
    await contains(".o-chart-dashboard-item[data-id='odoo_bar']", { visible: false }).click();
    expect(dataSource).toBe(model.getters.getChartDataSource(chartId));

    await contains(".o-chart-dashboard-item[data-id='odoo_line']", { visible: false }).click();
    expect(dataSource).toBe(model.getters.getChartDataSource(chartId));
});

test("can change granularity", async () => {
    const env = await makeSpreadsheetMockEnv();
    const setupModel = new Model({}, { custom: { odooDataProvider: new OdooDataProvider(env) } });
    const chartId = insertChartInSpreadsheet(setupModel, "odoo_line", {
        metaData: {
            groupBy: ["date:month"],
            resModel: "partner",
            measure: "__count",
            order: null,
        },
    });
    const { model } = await createDashboardActionWithData(setupModel.exportData());

    expect("select.o-chart-dashboard-item").toHaveValue("month");
    await contains("select.o-chart-dashboard-item", { visible: false }).select("quarter");
    expect(model.getters.getChartGranularity(chartId)).toEqual({
        fieldName: "date",
        granularity: "quarter",
    });
    expect(model.getters.getChartDefinition(chartId).metaData.groupBy).toEqual(["date:quarter"]);
});

test("can change type then change granularity and back to original type", async () => {
    const env = await makeSpreadsheetMockEnv();
    const setupModel = new Model({}, { custom: { odooDataProvider: new OdooDataProvider(env) } });
    const chartId = insertChartInSpreadsheet(setupModel, "odoo_line", {
        metaData: {
            groupBy: ["date:month"],
            resModel: "partner",
            measure: "__count",
            order: null,
        },
    });
    const { model } = await createDashboardActionWithData(setupModel.exportData());
    await contains(".o-chart-dashboard-item[data-id='odoo_pie']", { visible: false }).click();
    expect("select.o-chart-dashboard-item").toHaveValue("month");
    await contains("select.o-chart-dashboard-item", { visible: false }).select("quarter");
    expect(model.getters.getChartGranularity(chartId)).toEqual({
        fieldName: "date",
        granularity: "quarter",
    });
    expect(model.getters.getChartDefinition(chartId).type).toBe("odoo_pie");
    expect(model.getters.getChartDefinition(chartId).metaData.groupBy).toEqual(["date:quarter"]);
    await contains(".o-chart-dashboard-item[data-id='odoo_line']", { visible: false }).click();
    expect(model.getters.getChartDefinition(chartId).type).toBe("odoo_line");
    expect(model.getters.getChartGranularity(chartId)).toEqual({
        fieldName: "date",
        granularity: "quarter",
    });
    expect(model.getters.getChartDefinition(chartId).metaData.groupBy).toEqual(["date:quarter"]);
});

test("can change granularity then change type and back to original type", async () => {
    const env = await makeSpreadsheetMockEnv();
    const setupModel = new Model({}, { custom: { odooDataProvider: new OdooDataProvider(env) } });
    const chartId = insertChartInSpreadsheet(setupModel, "odoo_line", {
        metaData: {
            groupBy: ["date:month"],
            resModel: "partner",
            measure: "__count",
            order: null,
        },
    });
    const { model } = await createDashboardActionWithData(setupModel.exportData());
    await contains(".o-chart-dashboard-item[data-id='odoo_pie']", { visible: false }).click();
    await contains("select.o-chart-dashboard-item", { visible: false }).select("quarter");
    expect(model.getters.getChartDefinition(chartId).metaData.groupBy).toEqual(["date:quarter"]);
    expect(model.getters.getChartDefinition(chartId).type).toBe("odoo_pie");
    await contains(".o-chart-dashboard-item[data-id='odoo_line']", { visible: false }).click();
    expect(model.getters.getChartDefinition(chartId).type).toBe("odoo_line");
    expect(model.getters.getChartGranularity(chartId)).toEqual({
        fieldName: "date",
        granularity: "quarter",
    });
    expect(model.getters.getChartDefinition(chartId).metaData.groupBy).toEqual(["date:quarter"]);
});
