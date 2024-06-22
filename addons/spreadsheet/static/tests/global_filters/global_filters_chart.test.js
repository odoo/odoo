/** @ts-check */
import { mockDate } from "@odoo/hoot-mock";
import { defineSpreadsheetModels } from "@spreadsheet/../tests/helpers/data";
import { describe, expect, test } from "@odoo/hoot";

import { globalFiltersFieldMatchers } from "@spreadsheet/global_filters/plugins/global_filters_core_plugin";
import { createSpreadsheetWithChart } from "@spreadsheet/../tests/helpers/chart";
import { addGlobalFilter, setGlobalFilterValue } from "@spreadsheet/../tests/helpers/commands";

describe.current.tags("headless");
defineSpreadsheetModels();

/**
 * @typedef {import("@spreadsheet").DateGlobalFilter} DateGlobalFilter
 */

async function addChartGlobalFilter(model) {
    const chartId = model.getters.getChartIds(model.getters.getActiveSheetId())[0];
    /** @type {DateGlobalFilter}*/
    const filter = {
        id: "42",
        type: "date",
        label: "Last Year",
        rangeType: "fixedPeriod",
        defaultValue: { yearOffset: -1 },
    };
    await addGlobalFilter(model, filter, { chart: { [chartId]: { chain: "date", type: "date" } } });
}

test("Can add a chart global filter", async function () {
    const { model } = await createSpreadsheetWithChart();
    expect(model.getters.getGlobalFilters().length).toBe(0);
    await addChartGlobalFilter(model);
    expect(model.getters.getGlobalFilters().length).toBe(1);
    const chartId = model.getters.getChartIds(model.getters.getActiveSheetId())[0];
    const computedDomain = model.getters.getChartDataSource(chartId).getComputedDomain();
    expect(computedDomain.length).toBe(3);
    expect(computedDomain[0]).toBe("&");
});

test("Chart is loaded with computed domain", async function () {
    const { model } = await createSpreadsheetWithChart({
        mockRPC: function (route, { model, method, kwargs }) {
            if (model === "partner" && method === "web_read_group") {
                expect(kwargs.domain.length).toBe(3);
                expect(kwargs.domain[0]).toBe("&");
                expect(kwargs.domain[1][0]).toBe("date");
            }
        },
    });
    await addChartGlobalFilter(model);
});

test("Chart is impacted by global filter in dashboard mode", async function () {
    const { model } = await createSpreadsheetWithChart();
    expect(model.getters.getGlobalFilters().length).toBe(0);
    const chartId = model.getters.getChartIds(model.getters.getActiveSheetId())[0];

    /** @type {DateGlobalFilter}*/
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
    expect(computedDomain).toEqual([]);
    await setGlobalFilterValue(model, {
        id: "42",
        value: { yearOffset: -1 },
    });
    computedDomain = model.getters.getChartDataSource(chartId).getComputedDomain();
    expect(computedDomain.length).toBe(3);
    expect(computedDomain[0]).toBe("&");
});

test("field matching is removed when chart is deleted", async function () {
    const { model } = await createSpreadsheetWithChart();
    await addChartGlobalFilter(model);
    const [filter] = model.getters.getGlobalFilters();
    const [chartId] = model.getters.getChartIds(model.getters.getActiveSheetId());
    const matching = {
        chain: "date",
        type: "date",
    };
    expect(model.getters.getChartFieldMatch(chartId)[filter.id]).toEqual(matching);
    model.dispatch("DELETE_FIGURE", {
        sheetId: model.getters.getActiveSheetId(),
        id: chartId,
    });
    expect(globalFiltersFieldMatchers["chart"].getIds()).toEqual([], {
        message: "it should have removed the chart and its fieldMatching and datasource altogether",
    });
    model.dispatch("REQUEST_UNDO");
    expect(model.getters.getChartFieldMatch(chartId)[filter.id]).toEqual(matching);
    model.dispatch("REQUEST_REDO");
    expect(globalFiltersFieldMatchers["chart"].getIds()).toEqual([]);
});

test("field matching is removed when filter is deleted", async function () {
    mockDate("2022-07-10 00:00:00");
    const { model } = await createSpreadsheetWithChart();
    await addChartGlobalFilter(model);
    const [filter] = model.getters.getGlobalFilters();
    const [chartId] = model.getters.getChartIds(model.getters.getActiveSheetId());
    const matching = {
        chain: "date",
        type: "date",
    };
    expect(model.getters.getChartFieldMatch(chartId)[filter.id]).toEqual(matching);
    expect(model.getters.getChartDataSource(chartId).getComputedDomain()).toEqual([
        "&",
        ["date", ">=", "2021-01-01"],
        ["date", "<=", "2021-12-31"],
    ]);
    model.dispatch("REMOVE_GLOBAL_FILTER", {
        id: filter.id,
    });
    expect(model.getters.getChartFieldMatch(chartId)[filter.id]).toBe(undefined, {
        message: "it should have removed the chart and its fieldMatching and datasource altogether",
    });
    expect(model.getters.getChartDataSource(chartId).getComputedDomain()).toEqual([]);
    model.dispatch("REQUEST_UNDO");
    expect(model.getters.getChartFieldMatch(chartId)[filter.id]).toEqual(matching);
    expect(model.getters.getChartDataSource(chartId).getComputedDomain()).toEqual([
        "&",
        ["date", ">=", "2021-01-01"],
        ["date", "<=", "2021-12-31"],
    ]);
    model.dispatch("REQUEST_REDO");
    expect(model.getters.getChartFieldMatch(chartId)[filter.id]).toBe(undefined);
    expect(model.getters.getChartDataSource(chartId).getComputedDomain()).toEqual([]);
});
