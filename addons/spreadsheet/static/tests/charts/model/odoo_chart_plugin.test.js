import { animationFrame } from "@odoo/hoot-mock";
import { describe, expect, test } from "@odoo/hoot";

import { OdooBarChart } from "@spreadsheet/chart/odoo_chart/odoo_bar_chart";
import { OdooChart } from "@spreadsheet/chart/odoo_chart/odoo_chart";
import { OdooLineChart } from "@spreadsheet/chart/odoo_chart/odoo_line_chart";
import { ChartDataSource } from "@spreadsheet/chart/data_source/chart_data_source";

import {
    createSpreadsheetWithChart,
    insertChartInSpreadsheet,
} from "@spreadsheet/../tests/helpers/chart";
import { insertListInSpreadsheet } from "@spreadsheet/../tests/helpers/list";
import { createModelWithDataSource } from "@spreadsheet/../tests/helpers/model";
import { addGlobalFilter, updateChart } from "@spreadsheet/../tests/helpers/commands";
import { THIS_YEAR_GLOBAL_FILTER } from "@spreadsheet/../tests/helpers/global_filter";
import {
    mockService,
    makeServerError,
    fields,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import * as spreadsheet from "@odoo/o-spreadsheet";

import { user } from "@web/core/user";
import {
    getBasicServerData,
    defineSpreadsheetActions,
    defineSpreadsheetModels,
    Partner,
} from "@spreadsheet/../tests/helpers/data";
import { waitForDataLoaded } from "@spreadsheet/helpers/model";
import { setGlobalFilterValue } from "../../helpers/commands";

const { toZone } = spreadsheet.helpers;

const cumulativeDateServerData = getBasicServerData();
cumulativeDateServerData.models.partner.records = [
    { date: "2020-01-01", probability: 10 },
    { date: "2021-01-01", probability: 2 },
    { date: "2022-01-01", probability: 3 },
    { date: "2022-03-01", probability: 4 },
    { date: "2022-06-01", probability: 5 },
];

const cumulativeChartDefinition = {
    type: "odoo_line",
    metaData: {
        groupBy: ["date"],
        measure: "probability",
        order: null,
        resModel: "partner",
    },
    searchParams: {
        comparison: null,
        context: {},
        domain: [
            ["date", ">=", "2022-01-01"],
            ["date", "<=", "2022-12-31"],
        ],
        groupBy: [],
        orderBy: [],
    },
    cumulative: true,
    title: { text: "Partners" },
    dataSourceId: "42",
    id: "42",
};

const action = {
    domain: [
        "&",
        "&",
        ["date", ">=", "2022-01-01"],
        ["date", "<=", "2022-12-31"],
        "&",
        ["date", ">=", "2022-01-01"],
        ["date", "<", "2022-02-01"],
    ],
    name: "January 2022 / Probability",
    res_model: "partner",
    target: "current",
    type: "ir.actions.act_window",
    views: [
        [false, "list"],
        [false, "form"],
    ],
};

const fakeActionService = {
    doAction: async (request, options = {}) => {
        if (request.type === "ir.actions.act_window") {
            expect.step("do-action");
            expect(request).toEqual(action);
        }
    },
    loadAction(actionRequest) {
        expect.step("load-action");
        expect(actionRequest).toBe("test.my_action");
        return action;
    },
};

describe.current.tags("headless");
defineSpreadsheetModels();
defineSpreadsheetActions();

test("Can add an Odoo Bar chart", async () => {
    const { model } = await createSpreadsheetWithChart({ type: "odoo_bar" });
    const sheetId = model.getters.getActiveSheetId();
    expect(model.getters.getChartIds(sheetId).length).toBe(1);
    const chartId = model.getters.getChartIds(sheetId)[0];
    const chart = model.getters.getChart(chartId);
    expect(chart instanceof OdooBarChart).toBe(true);
    expect(chart.getDefinitionForExcel()).toBe(undefined);
    expect(model.getters.getChartRuntime(chartId).chartJsConfig.type).toBe("bar");
});

test("Can add an Odoo Line chart", async () => {
    const { model } = await createSpreadsheetWithChart({ type: "odoo_line" });
    const sheetId = model.getters.getActiveSheetId();
    expect(model.getters.getChartIds(sheetId).length).toBe(1);
    const chartId = model.getters.getChartIds(sheetId)[0];
    const chart = model.getters.getChart(chartId);
    expect(chart instanceof OdooLineChart).toBe(true);
    expect(chart.getDefinitionForExcel()).toBe(undefined);
    expect(model.getters.getChartRuntime(chartId).chartJsConfig.type).toBe("line");
});

test("Can add an Odoo Pie chart", async () => {
    const { model } = await createSpreadsheetWithChart({ type: "odoo_pie" });
    const sheetId = model.getters.getActiveSheetId();
    expect(model.getters.getChartIds(sheetId).length).toBe(1);
    const chartId = model.getters.getChartIds(sheetId)[0];
    const chart = model.getters.getChart(chartId);
    expect(chart instanceof OdooChart).toBe(true);
    expect(chart.getDefinitionForExcel()).toBe(undefined);
    expect(model.getters.getChartRuntime(chartId).chartJsConfig.type).toBe("pie");
});

test("A data source is added after a chart creation", async () => {
    const { model } = await createSpreadsheetWithChart();
    const sheetId = model.getters.getActiveSheetId();
    const chartId = model.getters.getChartIds(sheetId)[0];
    expect(model.getters.getChartDataSource(chartId)).not.toBe(undefined);
});

test("Odoo bar chart runtime loads the data", async () => {
    const { model } = await createSpreadsheetWithChart({
        type: "odoo_bar",
        mockRPC: async function (route, args) {
            if (args.method === "formatted_read_group") {
                expect.step("formatted_read_group");
            }
        },
    });
    const sheetId = model.getters.getActiveSheetId();
    const chartId = model.getters.getChartIds(sheetId)[0];
    // it should not be loaded eagerly
    expect.verifySteps([]);
    expect(model.getters.getChartRuntime(chartId).chartJsConfig.data).toEqual({
        datasets: [],
        labels: [],
    });
    await animationFrame();
    expect(model.getters.getChartRuntime(chartId).chartJsConfig.data).toEqual({
        datasets: [
            {
                backgroundColor: "#4EA7F2",
                borderColor: "#FFFFFF",
                borderWidth: 1,
                data: [1, 3],
                label: "Count",
                xAxisID: "x",
                yAxisID: "y",
                hidden: undefined,
            },
        ],
        labels: ["false", "true"],
    });
    // it should have loaded the data
    expect.verifySteps(["formatted_read_group"]);
});

test("Odoo pie chart runtime loads the data", async () => {
    const { model } = await createSpreadsheetWithChart({
        type: "odoo_pie",
        mockRPC: async function (route, args) {
            if (args.method === "formatted_read_group") {
                expect.step("formatted_read_group");
            }
        },
    });
    const sheetId = model.getters.getActiveSheetId();
    const chartId = model.getters.getChartIds(sheetId)[0];
    // it should not be loaded eagerly
    expect.verifySteps([]);
    expect(model.getters.getChartRuntime(chartId).chartJsConfig.data).toEqual({
        datasets: [],
        labels: [],
    });
    await animationFrame();
    expect(model.getters.getChartRuntime(chartId).chartJsConfig.data).toEqual({
        datasets: [
            {
                backgroundColor: ["#4EA7F2", "#EA6175", "#43C5B1"],
                borderColor: "#FFFFFF",
                data: [1, 3],
                hoverOffset: 10,
                label: "",
            },
        ],
        labels: ["false", "true"],
    });
    // it should have loaded the data
    expect.verifySteps(["formatted_read_group"]);
});

test("Odoo line chart runtime loads the data", async () => {
    const { model } = await createSpreadsheetWithChart({
        type: "odoo_line",
        mockRPC: async function (route, args) {
            if (args.method === "formatted_read_group") {
                expect.step("formatted_read_group");
            }
        },
    });
    const sheetId = model.getters.getActiveSheetId();
    const chartId = model.getters.getChartIds(sheetId)[0];
    // it should not be loaded eagerly
    expect.verifySteps([]);
    expect(model.getters.getChartRuntime(chartId).chartJsConfig.data).toEqual({
        datasets: [],
        labels: [],
    });
    await animationFrame();
    expect(model.getters.getChartRuntime(chartId).chartJsConfig.data).toEqual({
        datasets: [
            {
                backgroundColor: "#4EA7F2",
                borderColor: "#4EA7F2",
                data: [1, 3],
                label: "Count",
                tension: 0,
                fill: false,
                pointBackgroundColor: "#4EA7F2",
                pointRadius: 3,
                yAxisID: "y",
                hidden: undefined,
            },
        ],
        labels: ["false", "true"],
    });
    // it should have loaded the data
    expect.verifySteps(["formatted_read_group"]);
});

test("Area charts are supported", async () => {
    const { model } = await createSpreadsheetWithChart({ type: "odoo_line" });
    await waitForDataLoaded(model);
    const sheetId = model.getters.getActiveSheetId();
    const chartId = model.getters.getChartIds(sheetId)[0];
    const definition = model.getters.getChartDefinition(chartId);
    model.dispatch("UPDATE_CHART", {
        definition: { ...definition, fillArea: true, stacked: false },
        figureId: model.getters.getFigureIdFromChartId(chartId),
        chartId,
        sheetId,
    });
    let runtime = model.getters.getChartRuntime(chartId).chartJsConfig;
    expect(runtime.options.scales.x.stacked).toBe(undefined);
    expect(runtime.options.scales.y.stacked).toBe(false);
    expect(runtime.data.datasets[0].fill).toBe("origin");
    model.dispatch("UPDATE_CHART", {
        definition: { ...definition, fillArea: true, stacked: true },
        figureId: model.getters.getFigureIdFromChartId(chartId),
        chartId,
        sheetId,
    });
    runtime = model.getters.getChartRuntime(chartId).chartJsConfig;
    expect(runtime.options.scales.x.stacked).toBe(undefined);
    expect(runtime.options.scales.y.stacked).toBe(true);
    expect(runtime.data.datasets[0].fill).toBe("origin");
});

test("Data reloaded strictly upon domain update", async () => {
    const { model } = await createSpreadsheetWithChart({
        type: "odoo_line",
        mockRPC: async function (route, args) {
            if (args.method === "formatted_read_group") {
                expect.step("formatted_read_group");
            }
        },
    });
    const sheetId = model.getters.getActiveSheetId();
    const chartId = model.getters.getChartIds(sheetId)[0];
    const definition = model.getters.getChartDefinition(chartId);

    // force runtime computation
    model.getters.getChartRuntime(chartId);
    await animationFrame();
    // it should have loaded the data
    expect.verifySteps(["formatted_read_group"]);

    model.dispatch("UPDATE_CHART", {
        definition: {
            ...definition,
            searchParams: { ...definition.searchParams, domain: [["1", "=", "1"]] },
        },
        figureId: model.getters.getFigureIdFromChartId(chartId),
        chartId,
        sheetId,
    });
    // force runtime computation
    model.getters.getChartRuntime(chartId);
    await animationFrame();
    // it should have loaded the data with a new domain
    expect.verifySteps(["formatted_read_group"]);

    const newDefinition = model.getters.getChartDefinition(chartId);
    model.dispatch("UPDATE_CHART", {
        definition: {
            ...newDefinition,
            background: "#00FF00",
        },
        chartId,
        figureId: model.getters.getFigureIdFromChartId(chartId),
        sheetId,
    });
    // force runtime computation
    model.getters.getChartRuntime(chartId);
    await animationFrame();
    // it should have not have loaded the data since the domain was unchanged
    expect.verifySteps([]);
});

test("Data reloaded upon domain update for charts other than pie/bar/line", async () => {
    const { model } = await createSpreadsheetWithChart({
        type: "odoo_line",
        mockRPC: async function (route, args) {
            if (args.method === "formatted_read_group") {
                expect.step("formatted_read_group");
            }
        },
    });
    const sheetId = model.getters.getActiveSheetId();
    const chartId = model.getters.getChartIds(sheetId)[0];

    await waitForDataLoaded(model);
    expect.verifySteps(["formatted_read_group"]); // Data loaded

    updateChart(model, chartId, { type: "odoo_pie" });
    await waitForDataLoaded(model);
    expect.verifySteps([]); // Chart type changed

    const newDefinition = model.getters.getChartDefinition(chartId);
    updateChart(model, chartId, {
        searchParams: { ...newDefinition.searchParams, domain: [["1", "=", "1"]] },
    });
    await waitForDataLoaded(model);
    expect.verifySteps(["formatted_read_group"]); // Data re-loaded on domain update
});

test("Updating the domain keeps the global filters domain", async () => {
    let lastReadGroupDomain = undefined;
    const { model } = await createSpreadsheetWithChart({
        type: "odoo_line",
        mockRPC: async function (route, args) {
            if (args.method === "formatted_read_group") {
                expect.step("formatted_read_group");
                lastReadGroupDomain = args.kwargs.domain;
            }
        },
    });
    const sheetId = model.getters.getActiveSheetId();
    const chartId = model.getters.getChartIds(model.getters.getActiveSheetId())[0];
    const definition = model.getters.getChartDefinition(chartId);
    const filter = {
        id: "42",
        type: "relation",
        label: "filter",
        modelName: "product",
        defaultValue: { operator: "in", ids: [41] },
    };
    await addGlobalFilter(model, filter, {
        chart: { [chartId]: { chain: "product", type: "many2one" } },
    });

    model.getters.getChartRuntime(chartId); // force runtime computation
    await waitForDataLoaded(model);
    expect.verifySteps(["formatted_read_group"]);
    expect(lastReadGroupDomain).toEqual([["product", "in", [41]]]);

    const updatedDefinition = {
        ...definition,
        searchParams: { ...definition.searchParams, domain: [["1", "=", "1"]] },
    };
    model.dispatch("UPDATE_CHART", {
        definition: updatedDefinition,
        chartId,
        figureId: model.getters.getFigureIdFromChartId(chartId),
        sheetId,
    });

    model.getters.getChartRuntime(chartId); // force runtime computation
    await waitForDataLoaded(model);
    expect.verifySteps(["formatted_read_group"]);
    expect(lastReadGroupDomain).toEqual(["&", ["1", "=", "1"], ["product", "in", [41]]]);
});

test("Can import/export an Odoo chart", async () => {
    const { model } = await createModelWithDataSource();
    insertChartInSpreadsheet(model, "odoo_line");
    const data = model.exportData();
    const figures = data.sheets[0].figures;
    expect(figures.length).toBe(1);
    const figure = figures[0];
    expect(figure.tag).toBe("chart");
    expect(figure.data.type).toBe("odoo_line");
    const { model: m1 } = await createModelWithDataSource({ spreadsheetData: data });
    const sheetId = m1.getters.getActiveSheetId();
    expect(m1.getters.getChartIds(sheetId).length).toBe(1);
    const chartId = m1.getters.getChartIds(sheetId)[0];
    expect(model.getters.getChartDataSource(chartId)).not.toBe(undefined);
    expect(m1.getters.getChartRuntime(chartId).chartJsConfig.type).toBe("line");
});

test("can import (export) contextual domain", async function () {
    const chartId = "1";
    const uid = user.userId;
    const spreadsheetData = {
        sheets: [
            {
                figures: [
                    {
                        id: chartId,
                        x: 10,
                        y: 10,
                        width: 536,
                        height: 335,
                        tag: "chart",
                        data: {
                            chartId,
                            type: "odoo_line",
                            title: { text: "Partners" },
                            legendPosition: "top",
                            searchParams: {
                                domain: '[("foo", "=", uid)]',
                                groupBy: [],
                                orderBy: [],
                            },
                            metaData: {
                                groupBy: ["foo"],
                                measure: "__count",
                                resModel: "partner",
                            },
                        },
                    },
                ],
            },
        ],
    };
    const { model } = await createModelWithDataSource({
        spreadsheetData,
        mockRPC: function (route, args) {
            if (args.method === "formatted_read_group") {
                expect(args.kwargs.domain).toEqual([["foo", "=", uid]]);
                expect.step("formatted_read_group");
            }
        },
    });
    model.getters.getChartRuntime(chartId).chartJsConfig.data; // force loading the chart data
    await animationFrame();
    expect(model.exportData().sheets[0].figures[0].data.searchParams.domain).toBe(
        '[("foo", "=", uid)]',
        { message: "the domain is exported with the dynamic parts" }
    );
    expect.verifySteps(["formatted_read_group"]);
});

test("Can undo/redo an Odoo chart creation", async () => {
    const { model } = await createModelWithDataSource();
    insertChartInSpreadsheet(model, "odoo_line");
    const sheetId = model.getters.getActiveSheetId();
    const chartId = model.getters.getChartIds(sheetId)[0];
    expect(model.getters.getChartDataSource(chartId)).not.toBe(undefined);
    model.dispatch("REQUEST_UNDO");
    expect(model.getters.getChartIds(sheetId).length).toBe(0);
    model.dispatch("REQUEST_REDO");
    expect(model.getters.getChartDataSource(chartId)).not.toBe(undefined);
    expect(model.getters.getChartIds(sheetId).length).toBe(1);
});

test("charts with no legend", async () => {
    const { model } = await createSpreadsheetWithChart({ type: "odoo_pie" });
    insertChartInSpreadsheet(model, "odoo_bar");
    insertChartInSpreadsheet(model, "odoo_line");
    const sheetId = model.getters.getActiveSheetId();
    const [pieChartId, barChartId, lineChartId] = model.getters.getChartIds(sheetId);
    const pie = model.getters.getChartDefinition(pieChartId);
    const bar = model.getters.getChartDefinition(barChartId);
    const line = model.getters.getChartDefinition(lineChartId);
    expect(
        model.getters.getChartRuntime(pieChartId).chartJsConfig.options.plugins.legend.display
    ).toBe(true);
    expect(
        model.getters.getChartRuntime(barChartId).chartJsConfig.options.plugins.legend.display
    ).toBe(true);
    expect(
        model.getters.getChartRuntime(lineChartId).chartJsConfig.options.plugins.legend.display
    ).toBe(true);
    model.dispatch("UPDATE_CHART", {
        definition: {
            ...pie,
            legendPosition: "none",
        },
        chartId: pieChartId,
        figureId: model.getters.getFigureIdFromChartId(pieChartId),
        sheetId,
    });
    model.dispatch("UPDATE_CHART", {
        definition: {
            ...bar,
            legendPosition: "none",
        },
        chartId: barChartId,
        figureId: model.getters.getFigureIdFromChartId(barChartId),
        sheetId,
    });
    model.dispatch("UPDATE_CHART", {
        definition: {
            ...line,
            legendPosition: "none",
        },
        chartId: lineChartId,
        figureId: model.getters.getFigureIdFromChartId(lineChartId),
        sheetId,
    });
    expect(
        model.getters.getChartRuntime(pieChartId).chartJsConfig.options.plugins.legend.display
    ).toBe(false);
    expect(
        model.getters.getChartRuntime(barChartId).chartJsConfig.options.plugins.legend.display
    ).toBe(false);
    expect(
        model.getters.getChartRuntime(lineChartId).chartJsConfig.options.plugins.legend.display
    ).toBe(false);
});

test("Bar chart with stacked attribute is supported", async () => {
    const { model } = await createSpreadsheetWithChart({ type: "odoo_bar" });
    const sheetId = model.getters.getActiveSheetId();
    const chartId = model.getters.getChartIds(sheetId)[0];
    const definition = model.getters.getChartDefinition(chartId);
    model.dispatch("UPDATE_CHART", {
        definition: {
            ...definition,
            stacked: true,
        },
        chartId,
        figureId: model.getters.getFigureIdFromChartId(chartId),
        sheetId,
    });
    expect(model.getters.getChartRuntime(chartId).chartJsConfig.options.scales.x.stacked).toBe(
        true
    );
    expect(model.getters.getChartRuntime(chartId).chartJsConfig.options.scales.y.stacked).toBe(
        true
    );
    model.dispatch("UPDATE_CHART", {
        definition: {
            ...definition,
            stacked: false,
        },
        chartId,
        figureId: model.getters.getFigureIdFromChartId(chartId),
        sheetId,
    });
    expect(model.getters.getChartRuntime(chartId).chartJsConfig.options.scales.x.stacked).toBe(
        false
    );
    expect(model.getters.getChartRuntime(chartId).chartJsConfig.options.scales.y.stacked).toBe(
        false
    );
});

test("Can copy/paste Odoo chart", async () => {
    const { model } = await createSpreadsheetWithChart({ type: "odoo_pie" });
    const sheetId = model.getters.getActiveSheetId();
    const chartId = model.getters.getChartIds(sheetId)[0];
    model.dispatch("SELECT_FIGURE", { figureId: model.getters.getFigureIdFromChartId(chartId) });
    model.dispatch("COPY");
    model.dispatch("PASTE", { target: [toZone("A1")] });
    const chartIds = model.getters.getChartIds(sheetId);
    expect(chartIds.length).toBe(2);
    expect(model.getters.getChart(chartIds[1]) instanceof OdooChart).toBe(true);
    expect(JSON.stringify(model.getters.getChartRuntime(chartIds[1]))).toBe(
        JSON.stringify(model.getters.getChartRuntime(chartId))
    );

    expect(model.getters.getChart(chartId).dataSource).not.toBe(
        model.getters.getChart(chartIds[1]).dataSource,
        { message: "The datasource is also duplicated" }
    );
});

test("Can cut/paste Odoo chart", async () => {
    const { model } = await createSpreadsheetWithChart({ type: "odoo_pie" });
    const sheetId = model.getters.getActiveSheetId();
    const chartId = model.getters.getChartIds(sheetId)[0];
    const chartRuntime = model.getters.getChartRuntime(chartId);
    model.dispatch("SELECT_FIGURE", { figureId: model.getters.getFigureIdFromChartId(chartId) });
    model.dispatch("CUT");
    model.dispatch("PASTE", { target: [toZone("A1")] });
    const chartIds = model.getters.getChartIds(sheetId);
    expect(chartIds.length).toBe(1);
    expect(chartIds[0]).not.toBe(chartId);
    expect(model.getters.getChart(chartIds[0]) instanceof OdooChart).toBe(true);
    expect(JSON.stringify(model.getters.getChartRuntime(chartIds[0]))).toBe(
        JSON.stringify(chartRuntime)
    );
});

test("Duplicating a sheet correctly duplicates Odoo chart", async () => {
    const { model } = await createSpreadsheetWithChart({ type: "odoo_bar" });
    const sheetId = model.getters.getActiveSheetId();
    const secondSheetId = "secondSheetId";
    const chartId = model.getters.getChartIds(sheetId)[0];
    model.dispatch("DUPLICATE_SHEET", {
        sheetId,
        sheetIdTo: secondSheetId,
        sheetNameTo: "Next name",
    });
    const chartIds = model.getters.getChartIds(secondSheetId);
    expect(chartIds.length).toBe(1);
    expect(model.getters.getChart(chartIds[0]) instanceof OdooChart).toBe(true);
    expect(JSON.stringify(model.getters.getChartRuntime(chartIds[0]))).toBe(
        JSON.stringify(model.getters.getChartRuntime(chartId))
    );

    expect(model.getters.getChart(chartId).dataSource).not.toBe(
        model.getters.getChart(chartIds[0]).dataSource,
        { message: "The datasource is also duplicated" }
    );
});

test("Line chart with stacked attribute is supported", async () => {
    const { model } = await createSpreadsheetWithChart({ type: "odoo_line" });
    const sheetId = model.getters.getActiveSheetId();
    const chartId = model.getters.getChartIds(sheetId)[0];
    const definition = model.getters.getChartDefinition(chartId);
    model.dispatch("UPDATE_CHART", {
        definition: {
            ...definition,
            stacked: true,
        },
        chartId,
        figureId: model.getters.getFigureIdFromChartId(chartId),
        sheetId,
    });
    expect(model.getters.getChartRuntime(chartId).chartJsConfig.options.scales.x.stacked).toBe(
        undefined
    );
    expect(model.getters.getChartRuntime(chartId).chartJsConfig.options.scales.y.stacked).toBe(
        true
    );
    model.dispatch("UPDATE_CHART", {
        definition: {
            ...definition,
            stacked: false,
        },
        chartId,
        figureId: model.getters.getFigureIdFromChartId(chartId),
        sheetId,
    });
    expect(model.getters.getChartRuntime(chartId).chartJsConfig.options.scales.x.stacked).toBe(
        undefined
    );
    expect(model.getters.getChartRuntime(chartId).chartJsConfig.options.scales.y.stacked).toBe(
        false
    );
});

test("Load odoo chart spreadsheet with models that cannot be accessed", async function () {
    let hasAccessRights = true;
    const { model } = await createSpreadsheetWithChart({
        mockRPC: async function (route, args) {
            if (
                args.model === "partner" &&
                args.method === "formatted_read_group" &&
                !hasAccessRights
            ) {
                throw makeServerError({ description: "ya done!" });
            }
        },
    });
    const chartId = model.getters.getChartIds(model.getters.getActiveSheetId())[0];
    const chartDataSource = model.getters.getChartDataSource(chartId);
    await waitForDataLoaded(model);
    const data = chartDataSource.getData();
    expect(data.datasets.length).toBe(1);
    expect(data.labels.length).toBe(2);

    hasAccessRights = false;
    chartDataSource.load({ reload: true });
    await waitForDataLoaded(model);
    expect(chartDataSource.getData()).toEqual({ datasets: [], labels: [] });
});

test("Line chart to support cumulative data", async () => {
    const { model } = await createSpreadsheetWithChart({ type: "odoo_line" });
    const sheetId = model.getters.getActiveSheetId();
    const chartId = model.getters.getChartIds(sheetId)[0];
    const definition = model.getters.getChartDefinition(chartId);
    await waitForDataLoaded(model);
    expect(model.getters.getChartRuntime(chartId).chartJsConfig.data.datasets[0].data).toEqual([
        1, 3,
    ]);
    model.dispatch("UPDATE_CHART", {
        definition: {
            ...definition,
            cumulative: true,
        },
        chartId,
        figureId: model.getters.getFigureIdFromChartId(chartId),
        sheetId,
    });
    await waitForDataLoaded(model);
    expect(model.getters.getChartRuntime(chartId).chartJsConfig.data.datasets[0].data).toEqual([
        1, 4,
    ]);
    model.dispatch("UPDATE_CHART", {
        definition: {
            ...definition,
            cumulative: false,
        },
        chartId,
        figureId: model.getters.getFigureIdFromChartId(chartId),
        sheetId,
    });
    await waitForDataLoaded(model);
    expect(model.getters.getChartRuntime(chartId).chartJsConfig.data.datasets[0].data).toEqual([
        1, 3,
    ]);
});

test("cumulative line chart with past data before domain period without cumulated start", async () => {
    const { model } = await createSpreadsheetWithChart({
        type: "odoo_line",
        serverData: cumulativeDateServerData,
        definition: {
            ...cumulativeChartDefinition,
        },
    });
    const sheetId = model.getters.getActiveSheetId();
    const chartId = model.getters.getChartIds(sheetId)[0];
    await waitForDataLoaded(model);
    expect(model.getters.getChartRuntime(chartId).chartJsConfig.data.datasets[0].data).toEqual([
        3, 7, 12,
    ]);
    const figure = model.exportData().sheets[0].figures[0];
    expect(figure.data.cumulative).toBe(true);
    expect(figure.data.cumulatedStart).toBe(undefined);
});

test("cumulative line chart with past data before domain period with cumulated start", async () => {
    const { model } = await createSpreadsheetWithChart({
        type: "odoo_line",
        serverData: cumulativeDateServerData,
        definition: {
            ...cumulativeChartDefinition,
            cumulative: true,
            cumulatedStart: true,
        },
    });
    const sheetId = model.getters.getActiveSheetId();
    const chartId = model.getters.getChartIds(sheetId)[0];
    await waitForDataLoaded(model);
    expect(model.getters.getChartRuntime(chartId).chartJsConfig.data.datasets[0].data).toEqual([
        15, 19, 24,
    ]);
    const figure = model.exportData().sheets[0].figures[0];
    expect(figure.data.cumulative).toBe(true);
    expect(figure.data.cumulatedStart).toBe(true);
});

test("update existing chart to cumulate past data", async () => {
    const { model } = await createSpreadsheetWithChart({
        type: "odoo_line",
        serverData: cumulativeDateServerData,
        definition: {
            ...cumulativeChartDefinition,
            cumulative: true,
            cumulatedStart: false,
        },
    });
    const sheetId = model.getters.getActiveSheetId();
    const chartId = model.getters.getChartIds(sheetId)[0];
    await waitForDataLoaded(model);
    expect(model.getters.getChartRuntime(chartId).chartJsConfig.data.datasets[0].data).toEqual([
        3, 7, 12,
    ]);
    const figure = model.exportData().sheets[0].figures[0];
    expect(figure.data.cumulative).toBe(true);
    expect(figure.data.cumulatedStart).toBe(false);

    model.dispatch("UPDATE_CHART", {
        definition: {
            ...cumulativeChartDefinition,
            cumulatedStart: true,
        },
        chartId,
        figureId: model.getters.getFigureIdFromChartId(chartId),
        sheetId,
    });
    await waitForDataLoaded(model);
    expect(model.getters.getChartRuntime(chartId).chartJsConfig.data.datasets[0].data).toEqual([
        15, 19, 24,
    ]);
});

test("Can insert odoo chart from a different model", async () => {
    const { model } = await createModelWithDataSource();
    insertListInSpreadsheet(model, { model: "product", columns: ["name"] });
    await addGlobalFilter(model, THIS_YEAR_GLOBAL_FILTER);
    const sheetId = model.getters.getActiveSheetId();
    expect(model.getters.getChartIds(sheetId).length).toBe(0);
    insertChartInSpreadsheet(model);
    expect(model.getters.getChartIds(sheetId).length).toBe(1);
});

test("Odoo chart legend color changes with background color update", async () => {
    const { model } = await createSpreadsheetWithChart({ type: "odoo_bar" });
    const sheetId = model.getters.getActiveSheetId();
    const chartId = model.getters.getChartIds(sheetId)[0];
    const definition = model.getters.getChartDefinition(chartId);
    expect(
        model.getters.getChartRuntime(chartId).chartJsConfig.options.plugins.legend.labels.color
    ).toBe("#000000");
    model.dispatch("UPDATE_CHART", {
        definition: {
            ...definition,
            background: "#000000",
        },
        chartId,
        figureId: model.getters.getFigureIdFromChartId(chartId),
        sheetId,
    });
    expect(
        model.getters.getChartRuntime(chartId).chartJsConfig.options.plugins.legend.labels.color
    ).toBe("#FFFFFF");
});

test("Remove odoo chart when sheet is deleted", async () => {
    const { model } = await createSpreadsheetWithChart({ type: "odoo_line" });
    const sheetId = model.getters.getActiveSheetId();
    model.dispatch("CREATE_SHEET", {
        sheetId: model.uuidGenerator.smallUuid(),
        position: model.getters.getSheetIds().length,
    });
    expect(model.getters.getOdooChartIds().length).toBe(1);
    model.dispatch("DELETE_SHEET", { sheetId });
    expect(model.getters.getOdooChartIds().length).toBe(0);
});

test("Odoo chart datasource display name has a default when the chart title is empty", async () => {
    const { model } = await createSpreadsheetWithChart({ type: "odoo_line" });
    const sheetId = model.getters.getActiveSheetId();
    const chartId = model.getters.getChartIds(sheetId)[0];
    const definition = model.getters.getChartDefinition(chartId);
    expect(model.getters.getOdooChartDisplayName(chartId)).toBe("(#1) Partners");
    model.dispatch("UPDATE_CHART", {
        definition: {
            ...definition,
            title: { text: "" },
        },
        chartId,
        figureId: model.getters.getFigureIdFromChartId(chartId),
        sheetId,
    });
    expect(model.getters.getOdooChartDisplayName(chartId)).toBe("(#1) Odoo Line Chart");
});

test("See records when clicking on a bar chart bar", async () => {
    mockService("action", fakeActionService);
    const { model } = await createSpreadsheetWithChart({
        type: "odoo_bar",
        serverData: cumulativeDateServerData,
        definition: {
            ...cumulativeChartDefinition,
            type: "odoo_bar",
            actionXmlId: "test.my_action",
            cumulative: true,
        },
    });
    const sheetId = model.getters.getActiveSheetId();
    const chartId = model.getters.getChartIds(sheetId)[0];
    await waitForDataLoaded(model);
    const runtime = model.getters.getChartRuntime(chartId);
    expect.verifySteps([]);

    const event = { type: "click", native: new Event("click") };
    await runtime.chartJsConfig.options.onClick(event, [{ datasetIndex: 0, index: 0 }]);
    await animationFrame();
    expect.verifySteps(["load-action", "do-action"]);
});

test("See records in new tab on middle click of chart element", async () => {
    const fakeActionService = {
        doAction: async (request, options = {}) => {
            if (request.type === "ir.actions.act_window") {
                expect(request.res_model).toEqual("partner");
                if (options.newWindow) {
                    expect.step("do-action-new-window");
                }
            }
        },
    };
    mockService("action", fakeActionService);
    const { model } = await createSpreadsheetWithChart({ type: "odoo_bar" });
    const sheetId = model.getters.getActiveSheetId();
    const chartId = model.getters.getChartIds(sheetId)[0];
    await waitForDataLoaded(model);
    const runtime = model.getters.getChartRuntime(chartId);
    expect.verifySteps([]);

    const event = { type: "mouseup", native: new MouseEvent("mouseup", { button: 1 }) }; // Middle mouse button
    await runtime.chartJsConfig.options.onClick(event, [{ datasetIndex: 0, index: 0 }]);
    expect.verifySteps(["do-action-new-window"]);
});

test("See records when clicking on a line chart point", async () => {
    mockService("action", fakeActionService);
    const { model } = await createSpreadsheetWithChart({
        type: "odoo_line",
        serverData: cumulativeDateServerData,
        definition: {
            ...cumulativeChartDefinition,
            actionXmlId: "test.my_action",
            cumulative: true,
        },
    });
    const sheetId = model.getters.getActiveSheetId();
    const chartId = model.getters.getChartIds(sheetId)[0];
    await waitForDataLoaded(model);
    const runtime = model.getters.getChartRuntime(chartId);
    expect.verifySteps([]);

    const event = { type: "click", native: new Event("click") };
    await runtime.chartJsConfig.options.onClick(event, [{ datasetIndex: 0, index: 0 }]);
    await animationFrame();
    expect.verifySteps(["load-action", "do-action"]);
});

test("Actions not triggered by trendline clicks", async () => {
    mockService("action", fakeActionService);
    const { model } = await createSpreadsheetWithChart({
        type: "odoo_line",
        serverData: cumulativeDateServerData,
        definition: {
            ...cumulativeChartDefinition,
            cumulative: true,
            trend: "polynomial",
        },
    });

    const sheetId = model.getters.getActiveSheetId();
    const chartId = model.getters.getChartIds(sheetId)[0];
    await waitForDataLoaded(model);
    const runtime = model.getters.getChartRuntime(chartId);
    expect.verifySteps([]);

    const trendlineDatasetIndex = runtime.chartJsConfig.data.datasets.length;
    const event = { type: "click", native: new Event("click") };
    await runtime.chartJsConfig.options.onClick(event, [
        { datasetIndex: trendlineDatasetIndex, index: 0 },
    ]);
    await animationFrame();
    expect.verifySteps([]);
});

test("See records when clicking on a pie chart slice", async () => {
    const fakeActionService = {
        doAction: async (request, options = {}) => {
            if (request.type === "ir.actions.act_window") {
                expect.step("do-action");
                expect(request).toEqual({
                    ...action,
                    name: "January 2022",
                });
            }
        },
    };
    mockService("action", fakeActionService);
    const { model } = await createSpreadsheetWithChart({
        type: "odoo_pie",
        serverData: cumulativeDateServerData,
        definition: {
            ...cumulativeChartDefinition,
            type: "odoo_pie",
            cumulative: true,
        },
    });
    const sheetId = model.getters.getActiveSheetId();
    const chartId = model.getters.getChartIds(sheetId)[0];
    await waitForDataLoaded(model);

    const runtime = model.getters.getChartRuntime(chartId);
    expect.verifySteps([]);

    const event = { type: "click", native: new Event("click") };
    await runtime.chartJsConfig.options.onClick(event, [{ datasetIndex: 0, index: 0 }]);
    await animationFrame();
    expect.verifySteps(["do-action"]);
});

test("See records when clicking on a waterfall chart bar", async () => {
    let lastActionCalled = undefined;
    const fakeActionService = {
        doAction: async (request, options = {}) => (lastActionCalled = request),
        loadAction(actionRequest) {
            expect(actionRequest).toBe("test.my_action");
            return { type: "ir.actions.act_window" };
        },
    };
    mockService("action", fakeActionService);
    const serverData = getBasicServerData();
    serverData.models.partner.records = [
        { date: "2020-01-01", probability: 10, bar: true },
        { date: "2020-02-01", probability: 2, bar: true },
        { date: "2020-01-01", probability: 4, bar: false },
        { date: "2020-02-01", probability: 5, bar: false },
    ];
    const { model } = await createSpreadsheetWithChart({
        type: "odoo_waterfall",
        serverData,
        definition: {
            type: "odoo_waterfall",
            metaData: {
                groupBy: ["bar", "date"],
                measure: "probability",
                order: null,
                resModel: "partner",
            },
            searchParams: { context: {}, domain: [], groupBy: [], orderBy: [] },
            actionXmlId: "test.my_action",
            title: { text: "Partners" },
            dataSourceId: "42",
            id: "42",
            showSubTotals: true,
        },
    });
    const sheetId = model.getters.getActiveSheetId();
    const chartId = model.getters.getChartIds(sheetId)[0];
    await waitForDataLoaded(model);
    const runtime = model.getters.getChartRuntime(chartId);

    // First dataset
    const event = { type: "click", native: new Event("click") };
    await runtime.chartJsConfig.options.onClick(event, [{ datasetIndex: 0, index: 0 }]);
    await animationFrame();
    expect(lastActionCalled?.domain).toEqual([
        "&",
        "&",
        ["date", ">=", "2020-01-01"],
        ["date", "<", "2020-02-01"],
        ["bar", "=", false],
    ]);

    // First dataset subtotal
    await runtime.chartJsConfig.options.onClick(event, [{ datasetIndex: 0, index: 2 }]);
    await animationFrame();
    expect(lastActionCalled?.domain).toEqual([
        "&",
        "&",
        ["date", ">=", "2020-01-01"],
        ["date", "<", "2020-02-01"],
        [1, "=", 1],
    ]);

    // Second dataset
    await runtime.chartJsConfig.options.onClick(event, [{ datasetIndex: 0, index: 3 }]);
    await animationFrame();
    expect(lastActionCalled?.domain).toEqual([
        "&",
        "&",
        ["date", ">=", "2020-02-01"],
        ["date", "<", "2020-03-01"],
        ["bar", "=", false],
    ]);
});

test("See records when clicking on a geo chart country", async () => {
    const country_id = fields.Many2one({ string: "Country", relation: "res.country" });
    Partner._fields = { ...Partner._fields, country_id };
    Partner._records = [
        { id: 1, country_id: 1, probability: 10 },
        { id: 2, country_id: 2, probability: 2 },
    ];

    const fakeActionService = {
        doAction: async (request, options = {}) => {
            if (request.type === "ir.actions.act_window") {
                expect.step("do-action");
                expect(request.res_model).toBe("partner");
                expect(request.name).toBe("Belgium / Probability");
                expect(request.domain).toEqual([["country_id", "=", 1]]);
            }
        },
    };
    mockService("action", fakeActionService);
    const { model } = await createSpreadsheetWithChart({
        type: "odoo_geo",
        modelConfig: { external: { geoJsonService: { getAvailableRegions: () => [] } } },
        definition: {
            type: "odoo_geo",
            legendPosition: "top",
            metaData: {
                groupBy: ["country_id"],
                measure: "probability",
                resModel: "partner",
                order: null,
            },
            searchParams: { context: {}, domain: [], groupBy: [], orderBy: [] },
            cumulative: true,
            title: { text: "Partners" },
            dataSourceId: "42",
            id: "42",
        },
    });
    const sheetId = model.getters.getActiveSheetId();
    const chartId = model.getters.getChartIds(sheetId)[0];
    await waitForDataLoaded(model);

    const runtime = model.getters.getChartRuntime(chartId);
    expect.verifySteps([]);
    const mockElement = { feature: { properties: { name: "Belgium" } } };
    const event = { type: "click", native: new Event("click") };
    await runtime.chartJsConfig.options.onClick(event, [
        { datasetIndex: 0, index: 0, element: mockElement },
    ]);
    expect.verifySteps(["do-action"]);
});

test("See records when clicking on a sunburst chart slice", async () => {
    let lastActionCalled = undefined;
    const fakeActionService = {
        doAction: async (request, options = {}) => (lastActionCalled = request),
    };
    mockService("action", fakeActionService);
    const serverData = getBasicServerData();
    serverData.models.partner.records = [
        { date: "2020-01-01", probability: 10, bar: true },
        { date: "2020-02-01", probability: 2, bar: true },
        { date: "2020-01-01", probability: 4, bar: false },
        { date: "2020-02-01", probability: 5, bar: false },
    ];
    const { model } = await createSpreadsheetWithChart({
        type: "odoo_sunburst",
        serverData,
        definition: {
            type: "odoo_sunburst",
            metaData: {
                groupBy: ["date:month", "bar"],
                measure: "probability",
                order: null,
                resModel: "partner",
            },
            searchParams: { context: {}, domain: [], groupBy: [], orderBy: [] },
            title: { text: "Partners" },
            dataSourceId: "42",
            id: "42",
        },
    });
    const sheetId = model.getters.getActiveSheetId();
    const chartId = model.getters.getChartIds(sheetId)[0];
    await waitForDataLoaded(model);
    const runtime = model.getters.getChartRuntime(chartId);

    // Leaf value
    let mockChart = { data: { datasets: [{ data: [{ groups: ["January 2020", "false"] }] }] } };
    const event = { type: "click", native: new Event("click") };
    await runtime.chartJsConfig.options.onClick(event, [{ datasetIndex: 0, index: 0 }], mockChart);
    expect(lastActionCalled?.domain).toEqual([
        "&",
        "&",
        ["date", ">=", "2020-01-01"],
        ["date", "<", "2020-02-01"],
        ["bar", "=", false],
    ]);

    // Non-leaf value
    mockChart = { data: { datasets: [{ data: [{ groups: ["February 2020"] }] }] } };
    await runtime.chartJsConfig.options.onClick(event, [{ datasetIndex: 0, index: 0 }], mockChart);
    expect(lastActionCalled?.domain).toEqual([
        "&",
        ["date", ">=", "2020-02-01"],
        ["date", "<", "2020-03-01"],
    ]);
});

test("See records when clicking on a treemap chart item", async () => {
    let lastActionCalled = undefined;
    const fakeActionService = {
        doAction: async (request, options = {}) => (lastActionCalled = request),
    };
    mockService("action", fakeActionService);
    const serverData = getBasicServerData();
    serverData.models.partner.records = [
        { date: "2020-01-01", probability: 10, bar: true },
        { date: "2020-02-01", probability: 2, bar: true },
        { date: "2020-01-01", probability: 4, bar: false },
        { date: "2020-02-01", probability: 5, bar: false },
    ];
    const { model } = await createSpreadsheetWithChart({
        type: "odoo_treemap",
        serverData,
        definition: {
            type: "odoo_treemap",
            metaData: {
                groupBy: ["date:month", "bar"],
                measure: "probability",
                order: null,
                resModel: "partner",
            },
            searchParams: { context: {}, domain: [], groupBy: [], orderBy: [] },
            title: { text: "Partners" },
            dataSourceId: "42",
            id: "42",
        },
    });
    const sheetId = model.getters.getActiveSheetId();
    const chartId = model.getters.getChartIds(sheetId)[0];
    await waitForDataLoaded(model);
    const runtime = model.getters.getChartRuntime(chartId);

    function buildMockTreemapChart(groups) {
        const depth = groups.length - 1;
        const data = {};
        for (let i = 0; i <= depth; i++) {
            data[i] = groups[i];
        }
        return { data: { datasets: [{ data: [{ l: depth, _data: data }] }] } };
    }

    // Leaf value
    let mockChart = buildMockTreemapChart(["January 2020", "false"]);
    const event = { type: "click", native: new Event("click") };
    await runtime.chartJsConfig.options.onClick(event, [{ datasetIndex: 0, index: 0 }], mockChart);
    expect(lastActionCalled?.domain).toEqual([
        "&",
        "&",
        ["date", ">=", "2020-01-01"],
        ["date", "<", "2020-02-01"],
        ["bar", "=", false],
    ]);

    // Non-leaf value
    mockChart = buildMockTreemapChart(["February 2020"]);
    await runtime.chartJsConfig.options.onClick(event, [{ datasetIndex: 0, index: 0 }], mockChart);
    expect(lastActionCalled?.domain).toEqual([
        "&",
        ["date", ">=", "2020-02-01"],
        ["date", "<", "2020-03-01"],
    ]);
});

test("import/export action xml id", async () => {
    const { model } = await createSpreadsheetWithChart({
        type: "odoo_bar",
        definition: {
            type: "odoo_bar",
            metaData: {
                groupBy: [],
                measure: "probability",
                resModel: "partner",
            },
            searchParams: {
                domain: [],
                groupBy: [],
                orderBy: [],
            },
            actionXmlId: "test.my_action",
            cumulative: true,
            title: { text: "Partners" },
            dataSourceId: "42",
            id: "42",
        },
    });
    const exported = model.exportData();
    expect(exported.sheets[0].figures[0].data.actionXmlId).toBe("test.my_action");

    const { model: model2 } = await createModelWithDataSource({ spreadsheetData: exported });
    const sheetId = model2.getters.getActiveSheetId();
    const chartId = model2.getters.getChartIds(sheetId)[0];
    expect(model2.getters.getChartDefinition(chartId).actionXmlId).toBe("test.my_action");
});

test("Show values is taken into account in the runtime", async () => {
    const { model } = await createSpreadsheetWithChart({ type: "odoo_bar" });
    const sheetId = model.getters.getActiveSheetId();
    const chartId = model.getters.getChartIds(sheetId)[0];
    const definition = model.getters.getChartDefinition(chartId);
    model.dispatch("UPDATE_CHART", {
        definition: {
            ...definition,
            showValues: true,
        },
        chartId,
        figureId: model.getters.getFigureIdFromChartId(chartId),
        sheetId,
    });
    const runtime = model.getters.getChartRuntime(chartId);
    expect(runtime.chartJsConfig.options.plugins.chartShowValuesPlugin.showValues).toBe(true);
});

test("Odoo line and bar charts display only horizontal grid lines", async () => {
    const { model } = await createSpreadsheetWithChart({
        type: "odoo_line",
    });
    const sheetId = model.getters.getActiveSheetId();
    const chartId = model.getters.getChartIds(sheetId)[0];
    const lineChartConfig = model.getters.getChartRuntime(chartId).chartJsConfig;

    expect(lineChartConfig.options.scales.x.grid.display).toBe(false);
    expect(lineChartConfig.options.scales.y.grid.display).toBe(true);

    const lineChartDefinition = model.getters.getChartDefinition(chartId);
    model.dispatch("UPDATE_CHART", {
        definition: {
            ...lineChartDefinition,
            type: "odoo_bar",
        },
        chartId,
        figureId: model.getters.getFigureIdFromChartId(chartId),
        sheetId,
    });

    const barChartConfig = model.getters.getChartRuntime(chartId).chartJsConfig;

    expect(barChartConfig.options.scales.x.grid.display).toBe(false);
    expect(barChartConfig.options.scales.y.grid.display).toBe(true);
});

test("Can configure the chart datasets", async () => {
    const searchParams = { comparison: null, context: {}, domain: [], groupBy: [], orderBy: [] };
    const metaData = {
        groupBy: ["name", "bar"],
        measure: "probability",
        order: null,
        resModel: "partner",
    };

    const serverData = getBasicServerData();
    serverData.models.partner.records = [
        { name: "Frank", bar: true, probability: 10, foo: 5 },
        { name: "Marc", bar: false, probability: 2, foo: 5 },
    ];
    const { model } = await createSpreadsheetWithChart({
        type: "odoo_bar",
        serverData,
        definition: { type: "odoo_bar", metaData, searchParams, id: "42" },
    });
    await waitForDataLoaded(model);
    const sheetId = model.getters.getActiveSheetId();
    const chartId = model.getters.getChartIds(sheetId)[0];
    let definition = model.getters.getChartDefinition(chartId);
    expect(definition.dataSets).toEqual([{}, {}]);

    model.dispatch("UPDATE_CHART", {
        definition: { ...definition, dataSets: [{ label: "My dataset" }, { label: "Second" }] },
        chartId,
        figureId: model.getters.getFigureIdFromChartId(chartId),
        sheetId,
    });
    definition = model.getters.getChartDefinition(chartId);
    expect(definition.dataSets).toEqual([{ label: "My dataset" }, { label: "Second" }]);

    model.dispatch("UPDATE_CHART", {
        definition: {
            ...definition,
            searchParams: { ...searchParams, domain: [["bar", "=", false]] },
        },
        chartId,
        figureId: model.getters.getFigureIdFromChartId(chartId),
        sheetId,
    });
    model.dispatch("REFRESH_ALL_DATA_SOURCES");
    await waitForDataLoaded(model);
    definition = model.getters.getChartDefinition(chartId);
    // the second dataset was dropped from the definition since there is now only a single dataset in the data source
    expect(definition.dataSets).toEqual([{ label: "My dataset" }]);
});

test("Chart data source is updated when changing chart type", async () => {
    patchWithCleanup(ChartDataSource.prototype, {
        changeChartType(newMode) {
            expect.step("changeChartType");
            expect(newMode).toBe("line");
            super.changeChartType(newMode);
        },
    });

    const { model } = await createSpreadsheetWithChart({ type: "odoo_bar" });
    const sheetId = model.getters.getActiveSheetId();
    const chartId = model.getters.getChartIds(sheetId)[0];
    const chartDataSource = model.getters.getChartDataSource(chartId);

    model.dispatch("UPDATE_CHART", {
        definition: {
            ...model.getters.getChartDefinition(chartId),
            type: "odoo_line",
        },
        chartId,
        figureId: model.getters.getFigureIdFromChartId(chartId),
        sheetId,
    });
    expect.verifySteps(["changeChartType"]);
    expect(chartDataSource._metaData.mode).toBe("line");
});

test("Non-web chart types are using data source in 'bar' mode", async () => {
    const { model } = await createSpreadsheetWithChart({ type: "odoo_radar" });
    const sheetId = model.getters.getActiveSheetId();
    const chartId = model.getters.getChartIds(sheetId)[0];

    const chart = model.getters.getChart(chartId);
    expect(chart.metaData.mode).toBe("bar");

    const chartDataSource = model.getters.getChartDataSource(chartId);
    expect(chartDataSource._metaData.mode).toBe("bar");
});

test("Long labels are only truncated in the axis callback, not in the data given to the chart", async () => {
    const serverData = getBasicServerData();
    serverData.models.partner.records = [
        { name: "Guy", probability: 10 },
        { name: "Guy with a very very very long name", probability: 2 },
    ];
    const searchParams = { comparison: null, context: {}, domain: [], groupBy: [], orderBy: [] };
    const { model } = await createSpreadsheetWithChart({
        type: "odoo_line",
        serverData,
        definition: {
            type: "odoo_line",
            metaData: {
                groupBy: ["name"],
                measure: "probability",
                order: null,
                resModel: "partner",
            },
            searchParams,
            title: { text: "Partners" },
            dataSourceId: "42",
            id: "42",
        },
    });
    const sheetId = model.getters.getActiveSheetId();
    const chartId = model.getters.getChartIds(sheetId)[0];
    await waitForDataLoaded(model);
    const config = model.getters.getChartRuntime(chartId).chartJsConfig;
    expect(config.data.labels).toEqual(["Guy", "Guy with a very very very long name"]);

    const fakeChart = { getLabelForValue: (value) => value };
    const scaleCallback = config.options.scales.x.ticks.callback.bind(fakeChart);
    expect(scaleCallback("Guy")).toBe("Guy");
    expect(scaleCallback("Guy with a very very very long name")).toBe("Guy with a very very…");
});

test("can change chart granularity", async () => {
    const { model } = await createSpreadsheetWithChart({
        type: "odoo_bar",
        definition: {
            metaData: {
                groupBy: ["date:month"],
                measure: "probability",
                resModel: "partner",
            },
        },
    });
    const sheetId = model.getters.getActiveSheetId();
    const chartId = model.getters.getChartIds(sheetId)[0];
    model.dispatch("UPDATE_CHART_GRANULARITY", {
        chartId,
        granularity: "year",
    });
    expect(model.getters.getChartDefinition(chartId).metaData.groupBy).toEqual(["date:year"]);
});

test("changing chart granularity reloads data source once with global filter", async () => {
    onRpc("partner", "formatted_read_group", ({ kwargs }) => {
        expect.step(kwargs.groupby[0]);
        expect(kwargs.domain.length).toBe(3, { message: "Global filter domain is applied" });
    });
    const { model } = await createSpreadsheetWithChart({
        type: "odoo_bar",
        definition: {
            metaData: {
                groupBy: ["date:month"],
                measure: "probability",
                resModel: "partner",
            },
        },
    });
    const sheetId = model.getters.getActiveSheetId();
    const chartId = model.getters.getChartIds(sheetId)[0];
    await addGlobalFilter(
        model,
        { id: "42", type: "date", label: "Date", defaultValue: "last_90_days" },
        {
            chart: { [chartId]: { chain: "date", type: "date" } },
        }
    );
    model.getters.getChartRuntime(chartId); // load the data
    await animationFrame();
    expect.verifySteps(["date:month"]);
    model.dispatch("UPDATE_CHART_GRANULARITY", {
        chartId,
        granularity: "year",
    });
    model.getters.getChartRuntime(chartId); // load the data
    await animationFrame();
    expect.verifySteps(["date:year"]);
});

test("available granularities without filter", async () => {
    const { model } = await createSpreadsheetWithChart({
        type: "odoo_bar",
        definition: {
            metaData: {
                groupBy: ["date:month"],
                measure: "probability",
                resModel: "partner",
                order: null,
            },
        },
    });
    const sheetId = model.getters.getActiveSheetId();
    const chartId = model.getters.getChartIds(sheetId)[0];

    expect(model.getters.getAvailableChartGranularities(chartId).map((g) => g.value)).toEqual([
        "day",
        "week",
        "month",
        "quarter",
        "year",
    ]);
});

test("no available granularities when not grouped by a date", async () => {
    const { model } = await createSpreadsheetWithChart({
        type: "odoo_bar",
        definition: {
            metaData: {
                groupBy: ["name"],
                measure: "probability",
                resModel: "partner",
                order: null,
            },
        },
    });
    const sheetId = model.getters.getActiveSheetId();
    const chartId = model.getters.getChartIds(sheetId)[0];
    expect(model.getters.getAvailableChartGranularities(chartId)).toEqual([]);
});

test("available granularities with a date filter", async () => {
    const { model } = await createSpreadsheetWithChart({
        type: "odoo_bar",
        definition: {
            metaData: {
                groupBy: ["date:month"],
                measure: "probability",
                resModel: "partner",
                order: null,
            },
        },
    });
    const sheetId = model.getters.getActiveSheetId();
    const chartId = model.getters.getChartIds(sheetId)[0];
    const filterId = "42";
    await addGlobalFilter(
        model,
        { id: filterId, type: "date", label: "Date" },
        {
            chart: { [chartId]: { chain: "date", type: "date" } },
        }
    );
    model.updateMode("dashboard");
    expect(model.getters.getAvailableChartGranularities(chartId).map((g) => g.value)).toEqual([
        "day",
        "week",
        "month",
        "quarter",
        "year",
    ]);
    await setGlobalFilterValue(model, {
        id: filterId,
        value: { type: "relative", period: "last_90_days" },
    });
    expect(model.getters.getAvailableChartGranularities(chartId).map((g) => g.value)).toEqual([
        "day",
        "week",
        "month",
        "quarter",
    ]);
    await setGlobalFilterValue(model, {
        id: filterId,
        value: { type: "relative", period: "today" },
    });
    expect(model.getters.getAvailableChartGranularities(chartId).map((g) => g.value)).toEqual([
        "day",
    ]);
});

test("hour is an available granularity with a filtered datetime field", async () => {
    const { model } = await createSpreadsheetWithChart({
        type: "odoo_bar",
        definition: {
            metaData: {
                groupBy: ["create_date:month"],
                measure: "probability",
                resModel: "partner",
                order: null,
            },
        },
    });
    const sheetId = model.getters.getActiveSheetId();
    const chartId = model.getters.getChartIds(sheetId)[0];
    const filterId = "42";
    await addGlobalFilter(
        model,
        { id: filterId, type: "date", label: "Date" },
        {
            chart: { [chartId]: { chain: "create_date", type: "datetime" } },
        }
    );
    model.updateMode("dashboard");
    expect(model.getters.getAvailableChartGranularities(chartId).map((g) => g.value)).toEqual([
        "day",
        "week",
        "month",
        "quarter",
        "year",
    ]);
    await setGlobalFilterValue(model, {
        id: filterId,
        value: { type: "relative", period: "today" },
    });
    expect(model.getters.getAvailableChartGranularities(chartId).map((g) => g.value)).toEqual([
        "hour",
        "day",
    ]);
});

test("filtering a chart axis changes its granularity", async () => {
    const { model } = await createSpreadsheetWithChart({
        type: "odoo_bar",
        definition: {
            metaData: {
                groupBy: ["create_date:year"],
                measure: "probability",
                resModel: "partner",
                order: null,
            },
        },
    });
    const sheetId = model.getters.getActiveSheetId();
    const chartId = model.getters.getChartIds(sheetId)[0];
    const filterId = "42";
    await addGlobalFilter(
        model,
        { id: filterId, type: "date", label: "Date" },
        {
            chart: { [chartId]: { chain: "create_date", type: "datetime" } },
        }
    );
    model.updateMode("dashboard");

    const cases = [
        [{ type: "year", year: 2024 }, ["create_date:month"]],
        [{ type: "quarter", year: 2024, quarter: 1 }, ["create_date:month"]],
        [{ type: "month", year: 2024, month: 1 }, ["create_date:day"]],
        [{ type: "relative", period: "last_12_months" }, ["create_date:month"]],
        [{ type: "relative", period: "last_90_days" }, ["create_date:day"]],
        [{ type: "relative", period: "last_30_days" }, ["create_date:day"]],
        [{ type: "relative", period: "last_7_days" }, ["create_date:day"]],
        [{ type: "relative", period: "today" }, ["create_date:hour"]],
    ];

    for (const [value, expectedGroupBy] of cases) {
        await setGlobalFilterValue(model, {
            id: filterId,
            value,
        });
        expect(model.getters.getChartDefinition(chartId).metaData.groupBy).toEqual(
            expectedGroupBy,
            {
                message: `Expected groupBy to be ${expectedGroupBy} for value ${JSON.stringify(
                    value
                )}`,
            }
        );
    }
});

test("filtering doesn't change its granularity if not the horizontal axis", async () => {
    const { model } = await createSpreadsheetWithChart({
        type: "odoo_bar",
        definition: {
            metaData: {
                groupBy: ["create_date:year"],
                measure: "probability",
                resModel: "partner",
                order: null,
            },
        },
    });
    const sheetId = model.getters.getActiveSheetId();
    const chartId = model.getters.getChartIds(sheetId)[0];
    const filterId = "42";
    await addGlobalFilter(
        model,
        { id: filterId, type: "date", label: "Date" },
        {
            chart: { [chartId]: { chain: "date", type: "date" } }, // the horizontal axis is create_date, not date
        }
    );
    model.updateMode("dashboard");

    await setGlobalFilterValue(model, {
        id: filterId,
        value: { type: "relative", period: "last_7_days" },
    });
    expect(model.getters.getChartDefinition(chartId).metaData.groupBy).toEqual([
        "create_date:year",
    ]);
});

test("filtering preserves manually changed granularity", async () => {
    const { model } = await createSpreadsheetWithChart({
        type: "odoo_bar",
        definition: {
            metaData: {
                groupBy: ["create_date:year"],
                measure: "probability",
                resModel: "partner",
                order: null,
            },
        },
    });
    const sheetId = model.getters.getActiveSheetId();
    const chartId = model.getters.getChartIds(sheetId)[0];
    const filterId = "42";
    await addGlobalFilter(
        model,
        { id: filterId, type: "date", label: "Date" },
        {
            chart: { [chartId]: { chain: "create_date", type: "datetime" } },
        }
    );
    model.updateMode("dashboard");
    await setGlobalFilterValue(model, {
        id: filterId,
        value: { type: "relative", period: "last_90_days" },
    });
    expect(model.getters.getChartDefinition(chartId).metaData.groupBy).toEqual(["create_date:day"]);
    model.dispatch("UPDATE_CHART_GRANULARITY", {
        chartId,
        granularity: "week", // Manually change granularity to from day to week
    });

    // filtering on an equivalent range should not change the granularity
    await setGlobalFilterValue(model, {
        id: filterId,
        value: {
            type: "range",
            from: "2025-01-24",
            to: "2025-04-23",
        },
    });
    expect(model.getters.getChartDefinition(chartId).metaData.groupBy).toEqual([
        "create_date:week",
    ]);

    // changing to a non-compatible range should change the granularity
    await setGlobalFilterValue(model, {
        id: filterId,
        value: { type: "relative", period: "today" },
    });
    expect(model.getters.getChartDefinition(chartId).metaData.groupBy).toEqual([
        "create_date:hour",
    ]);
});

test("filtering on 'day' doesn't change to hour if not datetime", async () => {
    const { model } = await createSpreadsheetWithChart({
        type: "odoo_bar",
        definition: {
            metaData: {
                groupBy: ["date:year"],
                measure: "probability",
                resModel: "partner",
                order: null,
            },
        },
    });
    const sheetId = model.getters.getActiveSheetId();
    const chartId = model.getters.getChartIds(sheetId)[0];
    const filterId = "42";
    await addGlobalFilter(
        model,
        { id: filterId, type: "date", label: "Date" },
        {
            chart: { [chartId]: { chain: "date", type: "date" } },
        }
    );
    model.updateMode("dashboard");

    await setGlobalFilterValue(model, {
        id: filterId,
        value: { type: "relative", period: "today" },
    });
    expect(model.getters.getChartDefinition(chartId).metaData.groupBy).toEqual(["date:day"]);
});
