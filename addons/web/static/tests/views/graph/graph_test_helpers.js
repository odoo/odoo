import { before, expect } from "@odoo/hoot";
import { queryAllTexts, queryOne } from "@odoo/hoot-dom";
import { contains, findComponent, preloadBundle } from "@web/../tests/web_test_helpers";

import { ensureArray } from "@web/core/utils/arrays";
import { patch } from "@web/core/utils/patch";
import { GraphController } from "@web/views/graph/graph_controller";
import { GraphRenderer } from "@web/views/graph/graph_renderer";

/**
 * @typedef {"bar" | "line" | "pie"} GraphMode
 *
 * @typedef {import("@web/views/view").View} GraphView
 */

/**
 * @param {GraphView} view
 * @param {string | Iterable<string>} keys
 * @param {Record<string, any> | Iterable<Record<string, any>>} expectedDatasets
 */
export const checkDatasets = (view, keys, expectedDatasets) => {
    keys = ensureArray(keys);

    const datasets = getChart(view).data.datasets;
    const actualValues = [];
    for (const dataset of datasets) {
        const partialDataset = {};
        for (const key of keys) {
            partialDataset[key] = dataset[key];
        }
        actualValues.push(partialDataset);
    }
    expect(actualValues).toEqual(ensureArray(expectedDatasets));
};

/**
 * @param {GraphView} view
 * @param {GraphMode} mode
 */
export const checkModeIs = (view, mode) => {
    expect(getGraphModelMetaData(view).mode).toBe(mode);
    expect(getChart(view).config.type).toBe(mode);
    expect(getModeButton(mode)).toHaveClass("active");
};

/**
 * @param {GraphView} view
 * @param {{ lines: { label: string, value: string }[], title?: string }} expectedTooltip
 * @param {number} index
 * @param {number} datasetIndex
 */
export const checkTooltip = (view, { title, lines }, index, datasetIndex = null) => {
    // If the tooltip options are changed, this helper should change: we construct the dataPoints
    // similarly to Chart.js according to the values set for the tooltips options 'mode' and 'intersect'.
    const chart = getChart(view);
    const { datasets } = chart.data;
    const dataPoints = [];
    for (let i = 0; i < datasets.length; i++) {
        const dataset = datasets[i];
        const raw = dataset.data[index];
        if (raw !== undefined && (datasetIndex === null || datasetIndex === i)) {
            dataPoints.push({
                datasetIndex: i,
                dataIndex: index,
                raw,
            });
        }
    }
    chart.config.options.plugins.tooltip.external({
        tooltip: { opacity: 1, x: 1, y: 1, dataPoints },
    });
    const lineLabels = [];
    const lineValues = [];
    for (const line of lines) {
        lineLabels.push(line.label);
        lineValues.push(String(line.value));
    }

    expect(`.o_graph_custom_tooltip`).toHaveCount(1);
    expect(`table thead tr th.o_measure`).toHaveText(title || "Count");
    expect(queryAllTexts(`table tbody tr td small.o_label`)).toEqual(lineLabels);
    expect(queryAllTexts(`table tbody tr td.o_value`)).toEqual(lineValues);
};

/**
 * @param {"asc" | "desc"} direction
 */
export const clickSort = (direction) => contains(`.fa-sort-amount-${direction}`).click();

/**
 * @param {GraphView} view
 */
export const getChart = (view) => getGraphRenderer(view).chart;

/**
 * @param {GraphView} view
 */
export const getGraphModelMetaData = (view) => getGraphModel(view).metaData;

/**
 * @param {GraphMode} mode
 */
export const getModeButton = (mode) => queryOne`.o_graph_button[data-mode=${mode}]`;

/**
 * @param {GraphView} view
 */
export const getScaleY = (view) => getChart(view).config.options.scales.y;

/**
 * @param {GraphView} view
 */
export const getYAxisLabel = (view) => getChart(view).config.options.scales.y.title.text;

/**
 * @param {GraphView} view
 * @param {string | Iterable<string>} expectedLabels
 */
export function checkLabels(view, expectedLabels) {
    expect(getChart(view).data.labels.map(String)).toEqual(ensureArray(expectedLabels));
}

/**
 * @param {GraphView} view
 * @param {string | Iterable<string>} expectedLabels
 */
export function checkYTicks(view, expectedLabels) {
    const labels = getChart(view).scales.y.ticks.map((l) => l.label);
    expect(labels).toEqual(expectedLabels);
}

/**
 * @param {GraphView} view
 * @param {string | Iterable<string>} expectedLabels
 */
export function checkLegend(view, expectedLabels) {
    const chart = getChart(view);
    const labels = chart.config.options.plugins.legend.labels
        .generateLabels(chart)
        .map((o) => o.text);
    const expectedLabelsList = ensureArray(expectedLabels);
    expect(labels).toEqual(expectedLabelsList, {
        message: `Legend should be matching: ${expectedLabelsList
            .map((label) => `"${label}"`)
            .join(", ")}`,
    });
}

/**
 * @param {GraphView} view
 */
export async function clickOnDataset(view, options = {}) {
    const chart = getChart(view);
    const point = chart.getDatasetMeta(0).data[0].getCenterPoint();
    return contains(chart.canvas).click({ position: point, relative: true, ...options });
}

/**
 * @param {GraphView} view
 */
export function getGraphController(view) {
    return findComponent(view, (c) => c instanceof GraphController);
}

/**
 * @param {GraphView} view
 */
export function getGraphModel(view) {
    return getGraphController(view).model;
}

/**
 * @param {GraphView} view
 * @returns {GraphRenderer}
 */
export function getGraphRenderer(view) {
    return findComponent(view, (c) => c instanceof GraphRenderer);
}

/**
 * @param {GraphMode} mode
 */
export function selectMode(mode) {
    return contains(getModeButton(mode)).click();
}

/**
 * @param {GraphView} view
 * @param {string} text
 */
export async function clickOnLegend(view, text) {
    const chart = getChart(view);
    const index = chart.legend.legendItems.findIndex((e) => e.text === text);
    const { left, top, width, height } = chart.legend.legendHitBoxes[index];
    const point = {
        x: left + width / 2,
        y: top + height / 2,
    };
    return contains(chart.canvas).click({ position: point, relative: true });
}

/**
 * Helper to call at the start of a test suite using the Chart.js lib.
 *
 * It will:
 * - pre-load the Chart.js lib before tests are run;
 * - disable all animations in the lib.
 */
export function setupChartJsForTests() {
    preloadBundle("web.chartjs_lib");
    before(() => patch(Chart.defaults, { animation: false }));
}
