import { describe, expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-dom";
import { Model, components } from "@odoo/o-spreadsheet";
import { insertChartInSpreadsheet } from "@spreadsheet/../tests/helpers/chart";
import { addGlobalFilter, createBasicChart } from "@spreadsheet/../tests/helpers/commands";
import { makeSpreadsheetMockEnv } from "@spreadsheet/../tests/helpers/model";
import { OdooDataProvider } from "@spreadsheet/data_sources/odoo_data_provider";
import { createDashboardActionWithData } from "@spreadsheet_dashboard/../tests/helpers/dashboard_action";
import { defineSpreadsheetDashboardModels } from "@spreadsheet_dashboard/../tests/helpers/data";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { THIS_YEAR_GLOBAL_FILTER } from "@spreadsheet/../tests/helpers/global_filter";

describe.current.tags("desktop");
defineSpreadsheetDashboardModels();

function spyCharts() {
    const charts = {};
    patchWithCleanup(components.ChartJsComponent.prototype, {
        createChart(chartData) {
            super.createChart(chartData);
            charts[this.props.chartId] = this.chart;
        },
    });
    return charts;
}

test("Charts are animated only at first render", async () => {
    const env = await makeSpreadsheetMockEnv();
    const setupModel = new Model({}, { custom: { odooDataProvider: new OdooDataProvider(env) } });
    createBasicChart(setupModel, "chartId");
    const charts = spyCharts();
    const { model } = await createDashboardActionWithData(setupModel.exportData());

    expect(".o-figure").toHaveCount(1);
    expect(charts["chartId"].config.options.animation.animateRotate).toBe(true);

    // Scroll the figure out of the viewport and back in
    model.dispatch("SET_VIEWPORT_OFFSET", { offsetX: 0, offsetY: 500 });
    await animationFrame();
    await animationFrame();
    expect(".o-figure").toHaveCount(0);

    model.dispatch("SET_VIEWPORT_OFFSET", { offsetX: 0, offsetY: 0 });
    await animationFrame();
    expect(".o-figure").toHaveCount(1);
    expect(charts["chartId"].config.options.animation).toBe(false);
});

test("Animations are replayed only when chart data changes", async () => {
    const env = await makeSpreadsheetMockEnv();
    const setupModel = new Model({}, { custom: { odooDataProvider: new OdooDataProvider(env) } });
    const chartId = insertChartInSpreadsheet(setupModel);
    await addGlobalFilter(setupModel, THIS_YEAR_GLOBAL_FILTER, {
        chart: { [chartId]: { chain: "date", type: "date" } },
    });

    const charts = spyCharts();
    const { model } = await createDashboardActionWithData(setupModel.exportData());
    expect(charts[chartId].config.options.animation).toEqual({ animateRotate: true });

    // Change the chart data
    model.dispatch("SET_GLOBAL_FILTER_VALUE", { id: THIS_YEAR_GLOBAL_FILTER.id });
    await animationFrame();
    expect(charts[chartId].config.options.animation).toEqual({ animateRotate: true });

    // Dispatch a command that doesn't change the chart data
    model.dispatch("SET_GLOBAL_FILTER_VALUE", { id: THIS_YEAR_GLOBAL_FILTER.id });
    await animationFrame();
    expect(charts[chartId].config.options.animation).toBe(false);
});

test("Charts are animated when chart type changes", async () => {
    const env = await makeSpreadsheetMockEnv();
    const setupModel = new Model({}, { custom: { odooDataProvider: new OdooDataProvider(env) } });
    createBasicChart(setupModel, "chartId");
    const charts = spyCharts();
    const { model } = await createDashboardActionWithData(setupModel.exportData());

    expect(".o-figure").toHaveCount(1);
    expect(charts["chartId"].config.options.animation.animateRotate).toBe(true);
    delete charts["chartId"];

    const definition = model.getters.getChartDefinition("chartId");
    model.dispatch("UPDATE_CHART", {
        definition: { ...definition, type: "pie" },
        chartId: "chartId",
        figureId: model.getters.getFigureIdFromChartId("chartId"),
        sheetId: model.getters.getActiveSheetId(),
    });
    await animationFrame();

    expect(charts["chartId"].config.options.animation.animateRotate).toBe(true);
});
