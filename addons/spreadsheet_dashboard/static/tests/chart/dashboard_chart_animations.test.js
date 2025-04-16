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

describe.current.tags("desktop");
defineSpreadsheetDashboardModels();

function spyCharts() {
    const charts = {};
    patchWithCleanup(components.ChartJsComponent.prototype, {
        createChart(chartData) {
            super.createChart(chartData);
            charts[this.props.figureUI.id] = this.chart;
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
    const filter = {
        id: "filterId",
        type: "date",
        label: "Last Year",
        rangeType: "fixedPeriod",
        defaultValue: { yearOffset: -1 },
    };
    await addGlobalFilter(setupModel, filter, {
        chart: { [chartId]: { chain: "date", type: "date" } },
    });

    const charts = spyCharts();
    const { model } = await createDashboardActionWithData(setupModel.exportData());
    expect(charts[chartId].config.options.animation).toEqual({ animateRotate: true });

    // Change the chart data
    model.dispatch("SET_GLOBAL_FILTER_VALUE", { id: "filterId" });
    await animationFrame();
    expect(charts[chartId].config.options.animation).toEqual({ animateRotate: true });

    // Dispatch a command that doesn't change the chart data
    model.dispatch("SET_GLOBAL_FILTER_VALUE", { id: "filterId" });
    await animationFrame();
    expect(charts[chartId].config.options.animation).toBe(false);
});
