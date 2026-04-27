import { patchWithCleanup, contains, onRpc, makeServerError } from "@web/../tests/web_test_helpers";
import { animationFrame } from "@odoo/hoot-mock";
import { defineDocumentSpreadsheetModels } from "@documents_spreadsheet/../tests/helpers/data";
import { expect, test, beforeEach, getFixture, describe } from "@odoo/hoot";
import { createBasicChart } from "@spreadsheet/../tests/helpers/commands";
import { createSpreadsheet } from "@documents_spreadsheet/../tests/helpers/spreadsheet_test_utils";
import {
    createSpreadsheetFromGraphView,
    openChartSidePanel,
} from "@documents_spreadsheet/../tests/helpers/chart_helpers";
import { GraphRenderer } from "@web/views/graph/graph_renderer";
import { patchGraphSpreadsheet } from "@spreadsheet_edition/assets/graph_view/graph_view";
import { registries } from "@odoo/o-spreadsheet";
import * as dsHelpers from "@web/../tests/core/tree_editor/condition_tree_editor_test_helpers";
import { LoadableDataSource } from "@spreadsheet/data_sources/data_source";

defineDocumentSpreadsheetModels();
describe.current.tags("desktop");

const { chartSubtypeRegistry } = registries;

async function changeChartType(type) {
    await contains(".o-type-selector").click();
    await contains(`.o-chart-type-item[data-id="${type}"]`).click();
}

beforeEach(() => {
    patchWithCleanup(GraphRenderer.prototype, patchGraphSpreadsheet());
});

test("Open a chart panel", async () => {
    const { model, env } = await createSpreadsheetFromGraphView();
    await openChartSidePanel(model, env);
    expect(".o-sidePanel .o-sidePanelBody .o-chart").toHaveCount(1);
});

test("From an Odoo chart, can only change to an Odoo chart", async () => {
    const { model, env } = await createSpreadsheetFromGraphView();
    await openChartSidePanel(model, env);
    const target = getFixture();
    await contains(".o-type-selector").click();
    const odooChartTypes = chartSubtypeRegistry
        .getKeys()
        .filter((key) => key.startsWith("odoo_"))
        .sort();
    /** @type {NodeListOf<HTMLDivElement>} */
    const options = target.querySelectorAll(".o-chart-type-item");
    const optionValues = Array.from(options)
        .map((option) => option.dataset.id)
        .sort();
    expect(optionValues).toEqual(odooChartTypes);
});

test("From a spreadsheet chart, can only change to a spreadsheet chart", async () => {
    const { model, env } = await createSpreadsheet();
    createBasicChart(model, "1");
    await openChartSidePanel(model, env);
    const target = getFixture();
    await contains(".o-type-selector").click();
    /** @type {NodeListOf<HTMLDivElement>} */
    const options = target.querySelectorAll(".o-chart-type-item");
    const optionValues = Array.from(options)
        .map((option) => option.dataset.id)
        .sort();
    const nonOdooChartTypes = chartSubtypeRegistry
        .getKeys()
        .filter((key) => !key.startsWith("odoo_"))
        .sort();

    expect(optionValues).toEqual(nonOdooChartTypes);
});

test("Possible chart types are correct when switching from a spreadsheet to an odoo chart", async () => {
    const { model, env } = await createSpreadsheetFromGraphView();
    createBasicChart(model, "nonOdooChartId");
    await openChartSidePanel(model, env);
    const target = getFixture();
    await contains(".o-type-selector").click();

    /** @type {NodeListOf<HTMLDivElement>} */
    let options = target.querySelectorAll(".o-chart-type-item");
    let optionValues = Array.from(options).map((option) => option.dataset.id);
    expect(optionValues.every((value) => value.startsWith("odoo_"))).toBe(true);

    model.dispatch("SELECT_FIGURE", { id: "nonOdooChartId" });
    await animationFrame();

    await contains(".o-type-selector").click();
    options = target.querySelectorAll(".o-chart-type-item");
    optionValues = Array.from(options).map((option) => option.dataset.id);
    expect(optionValues.every((value) => !value.startsWith("odoo_"))).toBe(true);
});

test("Change odoo chart type", async () => {
    const { model, env } = await createSpreadsheetFromGraphView();
    const sheetId = model.getters.getActiveSheetId();
    const chartId = model.getters.getChartIds(sheetId)[0];
    expect(model.getters.getChart(chartId).type).toBe("odoo_bar");
    await openChartSidePanel(model, env);
    /** @type {HTMLSelectElement} */
    await changeChartType("odoo_pie");
    expect(model.getters.getChart(chartId).type).toBe("odoo_pie");

    await changeChartType("odoo_line");
    expect(model.getters.getChart(chartId).verticalAxisPosition).toBe("left");
    expect(model.getters.getChart(chartId).stacked).toBe(false);

    await changeChartType("odoo_bar");
    expect(model.getters.getChart(chartId).type).toBe("odoo_bar");
    expect(model.getters.getChart(chartId).stacked).toBe(false);

    await changeChartType("odoo_stacked_bar");
    expect(model.getters.getChart(chartId).type).toBe("odoo_bar");
    expect(model.getters.getChart(chartId).stacked).toBe(true);

    await changeChartType("odoo_stacked_line");
    expect(model.getters.getChart(chartId).type).toBe("odoo_line");
    expect(model.getters.getChart(chartId).stacked).toBe(true);
});

test("stacked line chart", async () => {
    const { model, env } = await createSpreadsheetFromGraphView();
    const sheetId = model.getters.getActiveSheetId();
    const chartId = model.getters.getChartIds(sheetId)[0];
    await openChartSidePanel(model, env);
    await changeChartType("odoo_stacked_line");

    // checked by default
    expect(model.getters.getChart(chartId).stacked).toBe(true);
    expect(".o-checkbox input[name='stackedBar']:checked").toHaveCount(1, {
        message: "checkbox should be checked",
    });

    // uncheck
    await contains(".o-checkbox input:checked").click();
    expect(model.getters.getChart(chartId).stacked).toBe(false);
    expect(".o-checkbox input[name='stackedBar']:checked").toHaveCount(0, {
        message: "checkbox should no longer be checked",
    });

    // check
    await contains(".o-checkbox input[name='stackedBar']").click();
    expect(model.getters.getChart(chartId).stacked).toBe(true);
    expect(".o-checkbox input:checked").toHaveCount(1, { message: "checkbox should be checked" });
});

test("Odoo area chart", async () => {
    const { model, env } = await createSpreadsheetFromGraphView();
    const sheetId = model.getters.getActiveSheetId();
    const chartId = model.getters.getChartIds(sheetId)[0];
    await openChartSidePanel(model, env);
    await changeChartType("odoo_area");

    let chartDefinition = model.getters.getChartDefinition(chartId);
    expect(chartDefinition.type).toBe("odoo_line");
    expect(chartDefinition.fillArea).toBe(true);
    expect(chartDefinition.stacked).toBe(false);

    await changeChartType("odoo_stacked_area");
    chartDefinition = model.getters.getChartDefinition(chartId);
    expect(chartDefinition.type).toBe("odoo_line");
    expect(chartDefinition.fillArea).toBe(true);
    expect(chartDefinition.stacked).toBe(true);
});

test("Change the title of a chart", async () => {
    const { model, env } = await createSpreadsheetFromGraphView();
    const sheetId = model.getters.getActiveSheetId();
    const chartId = model.getters.getChartIds(sheetId)[0];
    expect(model.getters.getChart(chartId).type).toBe("odoo_bar");
    await openChartSidePanel(model, env);
    const target = getFixture();
    await contains(".o-panel-design").click();
    /** @type {HTMLInputElement} */
    const input = target.querySelector(".o-chart-title input");
    expect(model.getters.getChart(chartId).title.text).toBe("PartnerGraph");
    await contains(input).edit("bla");
    expect(model.getters.getChart(chartId).title.text).toBe("bla");
});

test("Open chart odoo's data properties", async function () {
    const target = getFixture();
    const { model, env } = await createSpreadsheetFromGraphView();
    const sheetId = model.getters.getActiveSheetId();
    const chartId = model.getters.getChartIds(sheetId)[0];

    // opening from a chart
    model.dispatch("SELECT_FIGURE", { id: chartId });
    env.openSidePanel("ChartPanel");
    await animationFrame();

    const sections = target.querySelectorAll(".o-section");
    expect(sections.length).toBe(6, { message: "it should have 6 sections" });
    const [, , pivotModel, domain, , measures] = sections;

    expect(pivotModel.children[0]).toHaveText("Model");
    expect(pivotModel.children[1]).toHaveText("Partner (partner)");

    expect(domain.children[0]).toHaveText("Domain");
    expect(domain.children[1]).toHaveText("Match all records\nInclude archived");

    expect(measures.children[0].innerText.startsWith("Last updated at")).toBe(true);
});

test("Update the chart domain from the side panel", async function () {
    onRpc("/web/domain/validate", () => true);
    const { model, env } = await createSpreadsheetFromGraphView();
    const sheetId = model.getters.getActiveSheetId();
    const chartId = model.getters.getChartIds(sheetId)[0];
    model.dispatch("SELECT_FIGURE", { id: chartId });
    env.openSidePanel("ChartPanel");
    await animationFrame();
    const fixture = getFixture();
    await contains(".o_edit_domain").click();
    await dsHelpers.addNewRule();
    await contains(".modal-footer .btn-primary").click();
    expect(model.getters.getChartDefinition(chartId).searchParams.domain).toEqual([["id", "=", 1]]);
    expect(dsHelpers.getConditionText(fixture)).toBe("Id = 1");
});

test("Cumulative line chart", async () => {
    const { model, env } = await createSpreadsheetFromGraphView();
    const sheetId = model.getters.getActiveSheetId();
    const chartId = model.getters.getChartIds(sheetId)[0];
    await openChartSidePanel(model, env);
    await changeChartType("odoo_line");
    await contains(".o-checkbox input[name='cumulative']").click();
    // check
    expect(model.getters.getChart(chartId).cumulative).toBe(true);
    expect(".o-checkbox input[name='cumulative']:checked").toHaveCount(1, {
        message: "checkbox should be checked",
    });

    // uncheck
    await contains(".o-checkbox input[name='cumulative']").click();
    expect(model.getters.getChart(chartId).cumulative).toBe(false);
    expect(".o-checkbox input[name='cumulative']:checked").toHaveCount(0, {
        message: "checkbox should no longer be checked",
    });
});

describe("trend line", () => {
    test("activate trend line with the checkbox", async function () {
        const { model, env } = await createSpreadsheetFromGraphView();
        const sheetId = model.getters.getActiveSheetId();
        const chartId = model.getters.getChartIds(sheetId)[0];
        await openChartSidePanel(model, env);
        await contains(".o-panel-design").click();

        await contains("input[name='showTrendLine']").click();
        const definition = model.getters.getChartDefinition(chartId);
        expect(definition.trend).toEqual({
            type: "polynomial",
            order: 1,
            display: true,
        });
        const runtime = model.getters.getChartRuntime(chartId);
        expect(runtime.chartJsConfig.data.datasets.length).toBe(2);
    });

    test("Can change trend type", async function () {
        const { model, env } = await createSpreadsheetFromGraphView();
        const sheetId = model.getters.getActiveSheetId();
        const chartId = model.getters.getChartIds(sheetId)[0];
        await openChartSidePanel(model, env);
        await contains(".o-panel-design").click();
        await contains("input[name='showTrendLine']").click();

        let definition = model.getters.getChartDefinition(chartId);
        expect(definition.trend).toEqual({
            type: "polynomial",
            order: 1,
            display: true,
        });

        await contains(".trend-type-selector").select("logarithmic");
        definition = model.getters.getChartDefinition(chartId);
        expect(definition.trend?.type).toBe("logarithmic");
    });

    test("Can change polynomial degree", async function () {
        onRpc("web_read_group", () => {
            // return at least 3 groups to have a valid trend line
            return {
                groups: [
                    {
                        bar: true,
                        __count: 1,
                        __domain: [],
                    },
                    {
                        bar: false,
                        __count: 2,
                        __domain: [],
                    },
                    {
                        bar: null,
                        __count: 3,
                        __domain: [],
                    },
                ],
                length: 3,
            };
        });
        const { model, env } = await createSpreadsheetFromGraphView();
        const sheetId = model.getters.getActiveSheetId();
        const chartId = model.getters.getChartIds(sheetId)[0];
        await openChartSidePanel(model, env);
        await contains(".o-panel-design").click();
        await contains("input[name='showTrendLine']").click();

        let definition = model.getters.getChartDefinition(chartId);
        expect(definition.trend).toEqual({
            type: "polynomial",
            order: 1,
            display: true,
        });

        await contains(".trend-type-selector").select("polynomial");
        await contains(".trend-order-input").edit("3");
        definition = model.getters.getChartDefinition(chartId);
        expect(definition.trend?.order).toBe(3);
    });
});
test("Show values", async () => {
    const { model, env } = await createSpreadsheetFromGraphView();
    const sheetId = model.getters.getActiveSheetId();
    const chartId = model.getters.getChartIds(sheetId)[0];
    await openChartSidePanel(model, env);
    await contains(".o-panel-design").click();

    expect(model.getters.getChartDefinition(chartId).showValues).toBe(undefined);
    let options = model.getters.getChartRuntime(chartId).chartJsConfig.options;
    expect(options.plugins.chartShowValuesPlugin.showValues).toBe(undefined);

    await contains("input[name='showValues']").click();

    expect(model.getters.getChartDefinition(chartId).showValues).toBe(true);
    options = model.getters.getChartRuntime(chartId).chartJsConfig.options;
    expect(options.plugins.chartShowValuesPlugin.showValues).toBe(true);
});

test("An error is displayed in the side panel if the chart has invalid model", async function () {
    const { model, env } = await createSpreadsheetFromGraphView({
        mockRPC: async function (route, { model, method, kwargs }) {
            if (method === "fields_get") {
                throw makeServerError({ code: 404 });
            }
        },
    });
    await openChartSidePanel(model, env);

    expect(".o-validation-error").toHaveCount(1);
});

test("An spinner is displayed in the side panel if the chart model isn't loaded yet", async function () {
    let isDataSourceLoaded = false;
    patchWithCleanup(LoadableDataSource.prototype, {
        isReady: () => isDataSourceLoaded,
    });
    const { model, env } = await createSpreadsheetFromGraphView({});
    await openChartSidePanel(model, env);
    expect(".spinner-border").toHaveCount(1);

    isDataSourceLoaded = true;
    model.trigger("update");
    await animationFrame();

    expect(".spinner-border").toHaveCount(0);
});
