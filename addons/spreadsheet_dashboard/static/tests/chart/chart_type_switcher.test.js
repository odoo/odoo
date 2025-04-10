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

    expect(".o-dashboard-chart-select").toHaveCount(1);
    expect(".o-dashboard-chart-select [data-id='odoo_bar']").toHaveClass("selected");

    await contains(".o-dashboard-chart-select [data-id='odoo_line']", { visible: false }).click();

    const chartId = model.getters.getFigures(model.getters.getActiveSheetId())[0].id;
    const chartDefinition = model.getters.getChartDefinition(chartId);
    expect(chartDefinition.type).toBe("odoo_line");
});

test("Can change type of spreadsheet chart in dashboard", async () => {
    const setupModel = new Model();
    createBasicChart(setupModel, "chartId");
    const { model } = await createDashboardActionWithData(setupModel.exportData());

    expect(".o-dashboard-chart-select").toHaveCount(1);
    expect(".o-dashboard-chart-select [data-id='column']").toHaveClass("selected");

    await contains(".o-dashboard-chart-select [data-id='pie']", { visible: false }).click();

    const chartId = model.getters.getFigures(model.getters.getActiveSheetId())[0].id;
    const chartDefinition = model.getters.getChartDefinition(chartId);
    expect(chartDefinition.type).toBe("pie");
});

test("Can only change type of line/pie/bar charts", async () => {
    const env = await makeSpreadsheetMockEnv();
    const setupModel = new Model({}, { custom: { odooDataProvider: new OdooDataProvider(env) } });
    insertChartInSpreadsheet(setupModel, "odoo_radar");
    createScorecardChart(setupModel, "chartId");
    await createDashboardActionWithData(setupModel.exportData());

    expect(".o-dashboard-chart-select").toHaveCount(0);
});

test("Original chart configuration is kept when switching back and forth", async () => {
    const setupModel = new Model();
    createBasicChart(setupModel, "chartId", { type: "line", stacked: true, fillArea: true });
    const { model } = await createDashboardActionWithData(setupModel.exportData());

    await contains(".o-dashboard-chart-select [data-id='pie']", { visible: false }).click();
    await contains(".o-dashboard-chart-select [data-id='line']", { visible: false }).click();

    const chartDefinition = model.getters.getChartDefinition("chartId");
    expect(chartDefinition.type).toBe("line");
    expect(chartDefinition.stacked).toBe(true);
    expect(chartDefinition.fillArea).toBe(true);
});

test("Data source of cumulative line chart isn't reloaded after type change", async () => {
    const env = await makeSpreadsheetMockEnv();
    const setupModel = new Model({}, { custom: { odooDataProvider: new OdooDataProvider(env) } });
    const chartId = insertChartInSpreadsheet(setupModel, "odoo_line", { cumulative: true });
    const { model } = await createDashboardActionWithData(setupModel.exportData());

    const dataSource = model.getters.getChartDataSource(chartId);
    await contains(".o-dashboard-chart-select [data-id='odoo_bar']", { visible: false }).click();
    expect(dataSource).toBe(model.getters.getChartDataSource(chartId));

    await contains(".o-dashboard-chart-select [data-id='odoo_line']", { visible: false }).click();
    expect(dataSource).toBe(model.getters.getChartDataSource(chartId));
});
