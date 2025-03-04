import { describe, expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-dom";
import { Model, components } from "@odoo/o-spreadsheet";
import { insertChartInSpreadsheet } from "@spreadsheet/../tests/helpers/chart";
import {
    addGlobalFilter,
    createBasicChart,
    setCellContent,
} from "@spreadsheet/../tests/helpers/commands";
import { makeSpreadsheetMockEnv } from "@spreadsheet/../tests/helpers/model";
import { OdooDataProvider } from "@spreadsheet/data_sources/odoo_data_provider";
import { createDashboardActionWithData } from "@spreadsheet_dashboard/../tests/helpers/dashboard_action";
import { defineSpreadsheetDashboardModels } from "@spreadsheet_dashboard/../tests/helpers/data";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineSpreadsheetDashboardModels();

function spyCharts() {
    const charts = {};
    patchWithCleanup(components.ChartJsComponent.prototype, {
        createChart(chartData) {
            super.createChart(chartData);
            charts[this.props.figure.id] = this.chart;
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

    model.dispatch("SET_VIEWPORT_OFFSET", { offsetX: 0, offsetY: 500 }); // Scroll the figure out of the viewport
    await animationFrame();
    await animationFrame();
    expect(".o-figure").toHaveCount(0);

    model.dispatch("SET_VIEWPORT_OFFSET", { offsetX: 0, offsetY: 0 });
    await animationFrame();
    expect(".o-figure").toHaveCount(1);
    expect(charts["chartId"].config.options.animation).toBe(false);
});

test("Charts wait for all data sources to be loaded before displaying data and being animated", async () => {
    const env = await makeSpreadsheetMockEnv();
    const setupModel = new Model({}, { custom: { odooDataProvider: new OdooDataProvider(env) } });
    createBasicChart(setupModel, "chartId", { dataSets: [{ dataRange: "A1:A2" }] });
    setCellContent(setupModel, "A2", "42");
    const odooChartId = insertChartInSpreadsheet(setupModel, "odoo_bar");
    const charts = spyCharts();

    let markDataAsLoaded;
    patchWithCleanup(OdooDataProvider.prototype, {
        async notifyWhenPromiseResolves(promise) {
            this.pendingPromises.add(promise);
            markDataAsLoaded = () => {
                this.pendingPromises.clear();
                this.notify();
            };
        },
    });
    await createDashboardActionWithData(setupModel.exportData());

    expect(charts[odooChartId].config.options.animation).toBe(false);
    expect(charts[odooChartId].config.data.datasets).toEqual([]);
    expect(charts["chartId"].config.options.animation).toBe(false);
    expect(charts["chartId"].config.data.datasets).toEqual([]);

    markDataAsLoaded();
    await animationFrame();
    expect(charts[odooChartId].config.options.animation).toEqual({ animateRotate: true });
    expect(charts[odooChartId].config.data.datasets[0].data).toEqual([1, 3]);
    expect(charts["chartId"].config.options.animation).toEqual({ animateRotate: true });
    expect(charts["chartId"].config.data.datasets[0].data).toEqual([42]);
});

test("Animations are replayed on command invalidating chart data", async () => {
    const env = await makeSpreadsheetMockEnv();
    const setupModel = new Model({}, { custom: { odooDataProvider: new OdooDataProvider(env) } });
    createBasicChart(setupModel, "chartId");
    await addGlobalFilter(setupModel, {
        id: "filterId",
        type: "date",
        label: "Date Filter",
        rangeType: "fixedPeriod",
    });

    const charts = spyCharts();
    const { model } = await createDashboardActionWithData(setupModel.exportData());
    expect(charts["chartId"].config.options.animation).toEqual({ animateRotate: true });

    model.dispatch("SET_VIEWPORT_OFFSET", { offsetX: 0, offsetY: 500 }); // Scroll the figure out of the viewport
    await animationFrame();
    await animationFrame();
    model.dispatch("SET_VIEWPORT_OFFSET", { offsetX: 0, offsetY: 0 });
    await animationFrame();
    expect(charts["chartId"].config.options.animation).toBe(false);

    model.dispatch("CLEAR_GLOBAL_FILTER_VALUE", { id: "filterId" });
    await animationFrame();
    expect(charts["chartId"].config.options.animation).toEqual({ animateRotate: true });
});
