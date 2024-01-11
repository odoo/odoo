/** @odoo-module */

import { OdooBarChart } from "@spreadsheet/chart/odoo_chart/odoo_bar_chart";
import { OdooChart } from "@spreadsheet/chart/odoo_chart/odoo_chart";
import { OdooLineChart } from "@spreadsheet/chart/odoo_chart/odoo_line_chart";
import { nextTick } from "@web/../tests/helpers/utils";
import { createSpreadsheetWithChart, insertChartInSpreadsheet } from "../../utils/chart";
import { insertListInSpreadsheet } from "../../utils/list";
import { createModelWithDataSource, waitForDataSourcesLoaded } from "../../utils/model";
import { addGlobalFilter } from "../../utils/commands";
import { THIS_YEAR_GLOBAL_FILTER } from "../../utils/global_filter";
import * as spreadsheet from "@odoo/o-spreadsheet";
import { makeServerError } from "@web/../tests/helpers/mock_server";
import { session } from "@web/session";
import { getBasicServerData } from "../../utils/data";

const { toZone } = spreadsheet.helpers;

QUnit.module("spreadsheet > odoo chart plugin", {}, () => {
    QUnit.test("Can add an Odoo Bar chart", async (assert) => {
        const { model } = await createSpreadsheetWithChart({ type: "odoo_bar" });
        const sheetId = model.getters.getActiveSheetId();
        assert.strictEqual(model.getters.getChartIds(sheetId).length, 1);
        const chartId = model.getters.getChartIds(sheetId)[0];
        const chart = model.getters.getChart(chartId);
        assert.ok(chart instanceof OdooBarChart);
        assert.strictEqual(chart.getDefinitionForExcel(), undefined);
        assert.strictEqual(model.getters.getChartRuntime(chartId).chartJsConfig.type, "bar");
    });

    QUnit.test("Can add an Odoo Line chart", async (assert) => {
        const { model } = await createSpreadsheetWithChart({ type: "odoo_line" });
        const sheetId = model.getters.getActiveSheetId();
        assert.strictEqual(model.getters.getChartIds(sheetId).length, 1);
        const chartId = model.getters.getChartIds(sheetId)[0];
        const chart = model.getters.getChart(chartId);
        assert.ok(chart instanceof OdooLineChart);
        assert.strictEqual(chart.getDefinitionForExcel(), undefined);
        assert.strictEqual(model.getters.getChartRuntime(chartId).chartJsConfig.type, "line");
    });

    QUnit.test("Can add an Odoo Pie chart", async (assert) => {
        const { model } = await createSpreadsheetWithChart({ type: "odoo_pie" });
        const sheetId = model.getters.getActiveSheetId();
        assert.strictEqual(model.getters.getChartIds(sheetId).length, 1);
        const chartId = model.getters.getChartIds(sheetId)[0];
        const chart = model.getters.getChart(chartId);
        assert.ok(chart instanceof OdooChart);
        assert.strictEqual(chart.getDefinitionForExcel(), undefined);
        assert.strictEqual(model.getters.getChartRuntime(chartId).chartJsConfig.type, "pie");
    });

    QUnit.test("A data source is added after a chart creation", async (assert) => {
        const { model } = await createSpreadsheetWithChart();
        const sheetId = model.getters.getActiveSheetId();
        const chartId = model.getters.getChartIds(sheetId)[0];
        assert.ok(model.getters.getChartDataSource(chartId));
    });

    QUnit.test("Odoo bar chart runtime loads the data", async (assert) => {
        const { model } = await createSpreadsheetWithChart({
            type: "odoo_bar",
            mockRPC: async function (route, args) {
                if (args.method === "web_read_group") {
                    assert.step("web_read_group");
                }
            },
        });
        const sheetId = model.getters.getActiveSheetId();
        const chartId = model.getters.getChartIds(sheetId)[0];
        assert.verifySteps([], "it should not be loaded eagerly");
        assert.deepEqual(model.getters.getChartRuntime(chartId).chartJsConfig.data, {
            datasets: [],
            labels: [],
        });
        await nextTick();
        assert.deepEqual(model.getters.getChartRuntime(chartId).chartJsConfig.data, {
            datasets: [
                {
                    backgroundColor: "rgb(31,119,180)",
                    borderColor: "rgb(31,119,180)",
                    data: [1, 3],
                    label: "Count",
                },
            ],
            labels: ["false", "true"],
        });
        assert.verifySteps(["web_read_group"], "it should have loaded the data");
    });

    QUnit.test("Odoo pie chart runtime loads the data", async (assert) => {
        const { model } = await createSpreadsheetWithChart({
            type: "odoo_pie",
            mockRPC: async function (route, args) {
                if (args.method === "web_read_group") {
                    assert.step("web_read_group");
                }
            },
        });
        const sheetId = model.getters.getActiveSheetId();
        const chartId = model.getters.getChartIds(sheetId)[0];
        assert.verifySteps([], "it should not be loaded eagerly");
        assert.deepEqual(model.getters.getChartRuntime(chartId).chartJsConfig.data, {
            datasets: [],
            labels: [],
        });
        await nextTick();
        assert.deepEqual(model.getters.getChartRuntime(chartId).chartJsConfig.data, {
            datasets: [
                {
                    backgroundColor: ["rgb(31,119,180)", "rgb(255,127,14)", "rgb(174,199,232)"],
                    borderColor: "#FFFFFF",
                    data: [1, 3],
                    label: "",
                },
            ],
            labels: ["false", "true"],
        });
        assert.verifySteps(["web_read_group"], "it should have loaded the data");
    });

    QUnit.test("Odoo line chart runtime loads the data", async (assert) => {
        const { model } = await createSpreadsheetWithChart({
            type: "odoo_line",
            mockRPC: async function (route, args) {
                if (args.method === "web_read_group") {
                    assert.step("web_read_group");
                }
            },
        });
        const sheetId = model.getters.getActiveSheetId();
        const chartId = model.getters.getChartIds(sheetId)[0];
        assert.verifySteps([], "it should not be loaded eagerly");
        assert.deepEqual(model.getters.getChartRuntime(chartId).chartJsConfig.data, {
            datasets: [],
            labels: [],
        });
        await nextTick();
        assert.deepEqual(model.getters.getChartRuntime(chartId).chartJsConfig.data, {
            datasets: [
                {
                    backgroundColor: "#1F77B466",
                    borderColor: "rgb(31,119,180)",
                    data: [1, 3],
                    label: "Count",
                    lineTension: 0,
                    fill: "origin",
                    pointBackgroundColor: "rgb(31,119,180)",
                },
            ],
            labels: ["false", "true"],
        });
        assert.verifySteps(["web_read_group"], "it should have loaded the data");
    });

    QUnit.test("Data reloaded strictly upon domain update", async (assert) => {
        const { model } = await createSpreadsheetWithChart({
            type: "odoo_line",
            mockRPC: async function (route, args) {
                if (args.method === "web_read_group") {
                    assert.step("web_read_group");
                }
            },
        });
        const sheetId = model.getters.getActiveSheetId();
        const chartId = model.getters.getChartIds(sheetId)[0];
        const definition = model.getters.getChartDefinition(chartId);

        // force runtime computation
        model.getters.getChartRuntime(chartId);
        await nextTick();
        assert.verifySteps(["web_read_group"], "it should have loaded the data");

        model.dispatch("UPDATE_CHART", {
            definition: {
                ...definition,
                searchParams: { ...definition.searchParams, domain: [["1", "=", "1"]] },
            },
            id: chartId,
            sheetId,
        });
        // force runtime computation
        model.getters.getChartRuntime(chartId);
        await nextTick();
        assert.verifySteps(["web_read_group"], "it should have loaded the data with a new domain");

        const newDefinition = model.getters.getChartDefinition(chartId);
        model.dispatch("UPDATE_CHART", {
            definition: {
                ...newDefinition,
                type: "odoo_bar",
            },
            id: chartId,
            sheetId,
        });
        // force runtime computation
        model.getters.getChartRuntime(chartId);
        await nextTick();
        assert.verifySteps(
            [],
            "it should have not have loaded the data since the domain was unchanged"
        );
    });

    QUnit.test("Can import/export an Odoo chart", async (assert) => {
        const model = await createModelWithDataSource();
        insertChartInSpreadsheet(model, "odoo_line");
        const data = model.exportData();
        const figures = data.sheets[0].figures;
        assert.strictEqual(figures.length, 1);
        const figure = figures[0];
        assert.strictEqual(figure.tag, "chart");
        assert.strictEqual(figure.data.type, "odoo_line");
        const m1 = await createModelWithDataSource({ spreadsheetData: data });
        const sheetId = m1.getters.getActiveSheetId();
        assert.strictEqual(m1.getters.getChartIds(sheetId).length, 1);
        const chartId = m1.getters.getChartIds(sheetId)[0];
        assert.ok(m1.getters.getChartDataSource(chartId));
        assert.strictEqual(m1.getters.getChartRuntime(chartId).chartJsConfig.type, "line");
    });

    QUnit.test("can import (export) contextual domain", async function (assert) {
        const chartId = "1";
        const uid = session.user_context.uid;
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
                                type: "odoo_line",
                                title: "Partners",
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
        const model = await createModelWithDataSource({
            spreadsheetData,
            mockRPC: function (route, args) {
                if (args.method === "web_read_group") {
                    assert.deepEqual(args.kwargs.domain, [["foo", "=", uid]]);
                    assert.step("web_read_group");
                }
            },
        });
        model.getters.getChartRuntime(chartId).chartJsConfig.data; // force loading the chart data
        await nextTick();
        assert.strictEqual(
            model.exportData().sheets[0].figures[0].data.searchParams.domain,
            '[("foo", "=", uid)]',
            "the domain is exported with the dynamic parts"
        );
        assert.verifySteps(["web_read_group"]);
    });

    QUnit.test("Can undo/redo an Odoo chart creation", async (assert) => {
        const model = await createModelWithDataSource();
        insertChartInSpreadsheet(model, "odoo_line");
        const sheetId = model.getters.getActiveSheetId();
        const chartId = model.getters.getChartIds(sheetId)[0];
        assert.ok(model.getters.getChartDataSource(chartId));
        model.dispatch("REQUEST_UNDO");
        assert.strictEqual(model.getters.getChartIds(sheetId).length, 0);
        model.dispatch("REQUEST_REDO");
        assert.ok(model.getters.getChartDataSource(chartId));
        assert.strictEqual(model.getters.getChartIds(sheetId).length, 1);
    });

    QUnit.test("charts with no legend", async (assert) => {
        const { model } = await createSpreadsheetWithChart({ type: "odoo_pie" });
        insertChartInSpreadsheet(model, "odoo_bar");
        insertChartInSpreadsheet(model, "odoo_line");
        const sheetId = model.getters.getActiveSheetId();
        const [pieChartId, barChartId, lineChartId] = model.getters.getChartIds(sheetId);
        const pie = model.getters.getChartDefinition(pieChartId);
        const bar = model.getters.getChartDefinition(barChartId);
        const line = model.getters.getChartDefinition(lineChartId);
        assert.strictEqual(
            model.getters.getChartRuntime(pieChartId).chartJsConfig.options.plugins.legend.display,
            true
        );
        assert.strictEqual(
            model.getters.getChartRuntime(barChartId).chartJsConfig.options.plugins.legend.display,
            true
        );
        assert.strictEqual(
            model.getters.getChartRuntime(lineChartId).chartJsConfig.options.plugins.legend.display,
            true
        );
        model.dispatch("UPDATE_CHART", {
            definition: {
                ...pie,
                legendPosition: "none",
            },
            id: pieChartId,
            sheetId,
        });
        model.dispatch("UPDATE_CHART", {
            definition: {
                ...bar,
                legendPosition: "none",
            },
            id: barChartId,
            sheetId,
        });
        model.dispatch("UPDATE_CHART", {
            definition: {
                ...line,
                legendPosition: "none",
            },
            id: lineChartId,
            sheetId,
        });
        assert.strictEqual(
            model.getters.getChartRuntime(pieChartId).chartJsConfig.options.plugins.legend.display,
            false
        );
        assert.strictEqual(
            model.getters.getChartRuntime(barChartId).chartJsConfig.options.plugins.legend.display,
            false
        );
        assert.strictEqual(
            model.getters.getChartRuntime(lineChartId).chartJsConfig.options.plugins.legend.display,
            false
        );
    });

    QUnit.test("Bar chart with stacked attribute is supported", async (assert) => {
        const { model } = await createSpreadsheetWithChart({ type: "odoo_bar" });
        const sheetId = model.getters.getActiveSheetId();
        const chartId = model.getters.getChartIds(sheetId)[0];
        const definition = model.getters.getChartDefinition(chartId);
        model.dispatch("UPDATE_CHART", {
            definition: {
                ...definition,
                stacked: true,
            },
            id: chartId,
            sheetId,
        });
        assert.ok(model.getters.getChartRuntime(chartId).chartJsConfig.options.scales.x.stacked);
        assert.ok(model.getters.getChartRuntime(chartId).chartJsConfig.options.scales.y.stacked);
        model.dispatch("UPDATE_CHART", {
            definition: {
                ...definition,
                stacked: false,
            },
            id: chartId,
            sheetId,
        });
        assert.notOk(model.getters.getChartRuntime(chartId).chartJsConfig.options.scales.x.stacked);
        assert.notOk(model.getters.getChartRuntime(chartId).chartJsConfig.options.scales.y.stacked);
    });

    QUnit.test("Can copy/paste Odoo chart", async (assert) => {
        const { model } = await createSpreadsheetWithChart({ type: "odoo_pie" });
        const sheetId = model.getters.getActiveSheetId();
        const chartId = model.getters.getChartIds(sheetId)[0];
        model.dispatch("SELECT_FIGURE", { id: chartId });
        model.dispatch("COPY");
        model.dispatch("PASTE", { target: [toZone("A1")] });
        const chartIds = model.getters.getChartIds(sheetId);
        assert.strictEqual(chartIds.length, 2);
        assert.ok(model.getters.getChart(chartIds[1]) instanceof OdooChart);
        assert.strictEqual(
            JSON.stringify(model.getters.getChartRuntime(chartIds[1])),
            JSON.stringify(model.getters.getChartRuntime(chartId))
        );

        assert.notEqual(
            model.getters.getChart(chartId).dataSource,
            model.getters.getChart(chartIds[1]).dataSource,
            "The datasource is also duplicated"
        );
    });

    QUnit.test("Can cut/paste Odoo chart", async (assert) => {
        const { model } = await createSpreadsheetWithChart({ type: "odoo_pie" });
        const sheetId = model.getters.getActiveSheetId();
        const chartId = model.getters.getChartIds(sheetId)[0];
        const chartRuntime = model.getters.getChartRuntime(chartId);
        model.dispatch("SELECT_FIGURE", { id: chartId });
        model.dispatch("CUT");
        model.dispatch("PASTE", { target: [toZone("A1")] });
        const chartIds = model.getters.getChartIds(sheetId);
        assert.strictEqual(chartIds.length, 1);
        assert.notEqual(chartIds[0], chartId);
        assert.ok(model.getters.getChart(chartIds[0]) instanceof OdooChart);
        assert.strictEqual(
            JSON.stringify(model.getters.getChartRuntime(chartIds[0])),
            JSON.stringify(chartRuntime)
        );
    });

    QUnit.test("Duplicating a sheet correctly duplicates Odoo chart", async (assert) => {
        const { model } = await createSpreadsheetWithChart({ type: "odoo_bar" });
        const sheetId = model.getters.getActiveSheetId();
        const secondSheetId = "secondSheetId";
        const chartId = model.getters.getChartIds(sheetId)[0];
        model.dispatch("DUPLICATE_SHEET", { sheetId, sheetIdTo: secondSheetId });
        const chartIds = model.getters.getChartIds(secondSheetId);
        assert.strictEqual(chartIds.length, 1);
        assert.ok(model.getters.getChart(chartIds[0]) instanceof OdooChart);
        assert.strictEqual(
            JSON.stringify(model.getters.getChartRuntime(chartIds[0])),
            JSON.stringify(model.getters.getChartRuntime(chartId))
        );

        assert.notEqual(
            model.getters.getChart(chartId).dataSource,
            model.getters.getChart(chartIds[0]).dataSource,
            "The datasource is also duplicated"
        );
    });

    QUnit.test("Line chart with stacked attribute is supported", async (assert) => {
        const { model } = await createSpreadsheetWithChart({ type: "odoo_line" });
        const sheetId = model.getters.getActiveSheetId();
        const chartId = model.getters.getChartIds(sheetId)[0];
        const definition = model.getters.getChartDefinition(chartId);
        model.dispatch("UPDATE_CHART", {
            definition: {
                ...definition,
                stacked: true,
            },
            id: chartId,
            sheetId,
        });
        assert.notOk(model.getters.getChartRuntime(chartId).chartJsConfig.options.scales.x.stacked);
        assert.ok(model.getters.getChartRuntime(chartId).chartJsConfig.options.scales.y.stacked);
        model.dispatch("UPDATE_CHART", {
            definition: {
                ...definition,
                stacked: false,
            },
            id: chartId,
            sheetId,
        });
        assert.notOk(model.getters.getChartRuntime(chartId).chartJsConfig.options.scales.x.stacked);
        assert.notOk(model.getters.getChartRuntime(chartId).chartJsConfig.options.scales.y.stacked);
    });

    QUnit.test(
        "Load odoo chart spreadsheet with models that cannot be accessed",
        async function (assert) {
            let hasAccessRights = true;
            const { model } = await createSpreadsheetWithChart({
                mockRPC: async function (route, args) {
                    if (
                        args.model === "partner" &&
                        args.method === "web_read_group" &&
                        !hasAccessRights
                    ) {
                        throw makeServerError({ description: "ya done!" });
                    }
                },
            });
            const chartId = model.getters.getFigures(model.getters.getActiveSheetId())[0].id;
            const chartDataSource = model.getters.getChartDataSource(chartId);
            await waitForDataSourcesLoaded(model);
            const data = chartDataSource.getData();
            assert.equal(data.datasets.length, 1);
            assert.equal(data.labels.length, 2);

            hasAccessRights = false;
            chartDataSource.load({ reload: true });
            await waitForDataSourcesLoaded(model);
            assert.deepEqual(chartDataSource.getData(), { datasets: [], labels: [] });
        }
    );

    QUnit.test("Line chart to support cumulative data", async (assert) => {
        const { model } = await createSpreadsheetWithChart({ type: "odoo_line" });
        const sheetId = model.getters.getActiveSheetId();
        const chartId = model.getters.getChartIds(sheetId)[0];
        const definition = model.getters.getChartDefinition(chartId);
        await waitForDataSourcesLoaded(model);
        assert.deepEqual(
            model.getters.getChartRuntime(chartId).chartJsConfig.data.datasets[0].data,
            [1, 3]
        );
        model.dispatch("UPDATE_CHART", {
            definition: {
                ...definition,
                cumulative: true,
            },
            id: chartId,
            sheetId,
        });
        assert.deepEqual(
            model.getters.getChartRuntime(chartId).chartJsConfig.data.datasets[0].data,
            [1, 4]
        );
        model.dispatch("UPDATE_CHART", {
            definition: {
                ...definition,
                cumulative: false,
            },
            id: chartId,
            sheetId,
        });
        assert.deepEqual(
            model.getters.getChartRuntime(chartId).chartJsConfig.data.datasets[0].data,
            [1, 3]
        );
    });

    QUnit.test("cumulative line chart with past data before domain period", async (assert) => {
        const serverData = getBasicServerData();
        serverData.models.partner.records = [
            { date: "2020-01-01", probability: 10 },
            { date: "2021-01-01", probability: 2 },
            { date: "2022-01-01", probability: 3 },
            { date: "2022-03-01", probability: 4 },
            { date: "2022-06-01", probability: 5 },
        ];
        const { model } = await createSpreadsheetWithChart({
            type: "odoo_line",
            serverData,
            definition: {
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
                title: "Partners",
                dataSourceId: "42",
                id: "42",
            },
        });
        const sheetId = model.getters.getActiveSheetId();
        const chartId = model.getters.getChartIds(sheetId)[0];
        await waitForDataSourcesLoaded(model);

        assert.deepEqual(
            model.getters.getChartRuntime(chartId).chartJsConfig.data.datasets[0].data,
            [15, 19, 24]
        );
    });

    QUnit.test("Can insert odoo chart from a different model", async (assert) => {
        const model = await createModelWithDataSource();
        insertListInSpreadsheet(model, { model: "product", columns: ["name"] });
        await addGlobalFilter(model, THIS_YEAR_GLOBAL_FILTER);
        const sheetId = model.getters.getActiveSheetId();
        assert.strictEqual(model.getters.getChartIds(sheetId).length, 0);
        insertChartInSpreadsheet(model);
        assert.strictEqual(model.getters.getChartIds(sheetId).length, 1);
    });
});
