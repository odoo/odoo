/** @odoo-module alias=@web/../tests/views/graph_view_tests default=false */

import { click, findChildren, triggerEvent } from "@web/../tests/helpers/utils";
import { ensureArray } from "@web/core/utils/arrays";

// TODO: remove when dependant modules are converted

export function checkLabels(assert, graph, expectedLabels) {
    const labels = getGraphRenderer(graph).chart.data.labels.map((l) => l.toString());
    assert.deepEqual(labels, expectedLabels);
}

export function checkLegend(assert, graph, expectedLegendLabels) {
    expectedLegendLabels = ensureArray(expectedLegendLabels);
    const { chart } = getGraphRenderer(graph);
    const actualLegendLabels = chart.config.options.plugins.legend.labels
        .generateLabels(chart)
        .map((o) => o.text);
    assert.deepEqual(actualLegendLabels, expectedLegendLabels);
}

export function clickOnDataset(graph) {
    const { chart } = getGraphRenderer(graph);
    const meta = chart.getDatasetMeta(0);
    const rectangle = chart.canvas.getBoundingClientRect();
    const point = meta.data[0].getCenterPoint();
    return triggerEvent(chart.canvas, null, "click", {
        pageX: rectangle.left + point.x,
        pageY: rectangle.top + point.y,
    });
}

export function getGraphRenderer(graph) {
    for (const { component } of Object.values(findChildren(graph).children)) {
        if (component.chart) {
            return component;
        }
    }
    return null;
}

export function selectMode(el, mode) {
    return click(el, `.o_graph_button[data-mode="${mode}"`);
}
