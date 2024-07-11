/** @odoo-module */

import { globalFiltersFieldMatchers } from "../../src/global_filters/plugins/global_filters_core_plugin";
import { createSpreadsheetWithChart } from "../utils/chart";
import { addGlobalFilter, setGlobalFilterValue } from "../utils/commands";
import { patchDate } from "@web/../tests/helpers/utils";

async function addChartGlobalFilter(model) {
    const chartId = model.getters.getChartIds(model.getters.getActiveSheetId())[0];
    const filter = {
        id: "42",
        type: "date",
        label: "Last Year",
        rangeType: "fixedPeriod",
        defaultValue: { yearOffset: -1 },
    };
    await addGlobalFilter(model, filter, { chart: { [chartId]: { chain: "date", type: "date" } } });
}

QUnit.module("spreadsheet > Global filters chart", {}, () => {
    QUnit.test("Can add a chart global filter", async function (assert) {
        const { model } = await createSpreadsheetWithChart();
        assert.equal(model.getters.getGlobalFilters().length, 0);
        await addChartGlobalFilter(model);
        assert.equal(model.getters.getGlobalFilters().length, 1);
        const chartId = model.getters.getChartIds(model.getters.getActiveSheetId())[0];
        const computedDomain = model.getters.getChartDataSource(chartId).getComputedDomain();
        assert.equal(computedDomain.length, 3);
        assert.equal(computedDomain[0], "&");
    });

    QUnit.test("Chart is loaded with computed domain", async function (assert) {
        const { model } = await createSpreadsheetWithChart({
            mockRPC: function (route, { model, method, kwargs }) {
                if (model === "partner" && method === "web_read_group") {
                    assert.strictEqual(kwargs.domain.length, 3);
                    assert.strictEqual(kwargs.domain[0], "&");
                    assert.strictEqual(kwargs.domain[1][0], "date");
                }
            },
        });
        await addChartGlobalFilter(model);
    });

    QUnit.test("Chart is impacted by global filter in dashboard mode", async function (assert) {
        const { model } = await createSpreadsheetWithChart();
        assert.equal(model.getters.getGlobalFilters().length, 0);
        const chartId = model.getters.getChartIds(model.getters.getActiveSheetId())[0];
        const filter = {
            id: "42",
            type: "date",
            label: "Last Year",
            rangeType: "fixedPeriod",
        };
        await addGlobalFilter(model, filter, {
            chart: { [chartId]: { chain: "date", type: "date" } },
        });
        model.updateMode("dashboard");
        let computedDomain = model.getters.getChartDataSource(chartId).getComputedDomain();
        assert.deepEqual(computedDomain, []);
        await setGlobalFilterValue(model, {
            id: "42",
            value: { yearOffset: -1 },
        });
        computedDomain = model.getters.getChartDataSource(chartId).getComputedDomain();
        assert.equal(computedDomain.length, 3);
        assert.equal(computedDomain[0], "&");
    });

    QUnit.test("field matching is removed when chart is deleted", async function (assert) {
        const { model } = await createSpreadsheetWithChart();
        await addChartGlobalFilter(model);
        const [filter] = model.getters.getGlobalFilters();
        const [chartId] = model.getters.getChartIds(model.getters.getActiveSheetId());
        const matching = {
            chain: "date",
            type: "date",
        };
        assert.deepEqual(model.getters.getChartFieldMatch(chartId)[filter.id], matching);
        model.dispatch("DELETE_FIGURE", {
            sheetId: model.getters.getActiveSheetId(),
            id: chartId,
        });
        assert.deepEqual(
            globalFiltersFieldMatchers["chart"].getIds(),
            [],
            "it should have removed the chart and its fieldMatching and datasource altogether"
        );
        model.dispatch("REQUEST_UNDO");
        assert.deepEqual(model.getters.getChartFieldMatch(chartId)[filter.id], matching);
        model.dispatch("REQUEST_REDO");
        assert.deepEqual(globalFiltersFieldMatchers["chart"].getIds(), []);
    });

    QUnit.test("field matching is removed when filter is deleted", async function (assert) {
        patchDate(2022, 6, 10, 0, 0, 0);
        const { model } = await createSpreadsheetWithChart();
        await addChartGlobalFilter(model);
        const [filter] = model.getters.getGlobalFilters();
        const [chartId] = model.getters.getChartIds(model.getters.getActiveSheetId());
        const matching = {
            chain: "date",
            type: "date",
        };
        assert.deepEqual(model.getters.getChartFieldMatch(chartId)[filter.id], matching);
        assert.deepEqual(model.getters.getChartDataSource(chartId).getComputedDomain(), [
            "&",
            ["date", ">=", "2021-01-01"],
            ["date", "<=", "2021-12-31"],
        ]);
        model.dispatch("REMOVE_GLOBAL_FILTER", {
            id: filter.id,
        });
        assert.deepEqual(
            model.getters.getChartFieldMatch(chartId)[filter.id],
            undefined,
            "it should have removed the chart and its fieldMatching and datasource altogether"
        );
        assert.deepEqual(model.getters.getChartDataSource(chartId).getComputedDomain(), []);
        model.dispatch("REQUEST_UNDO");
        assert.deepEqual(model.getters.getChartFieldMatch(chartId)[filter.id], matching);
        assert.deepEqual(model.getters.getChartDataSource(chartId).getComputedDomain(), [
            "&",
            ["date", ">=", "2021-01-01"],
            ["date", "<=", "2021-12-31"],
        ]);
        model.dispatch("REQUEST_REDO");
        assert.deepEqual(model.getters.getChartFieldMatch(chartId)[filter.id], undefined);
        assert.deepEqual(model.getters.getChartDataSource(chartId).getComputedDomain(), []);
    });
});
