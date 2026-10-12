import { loadBundle } from "@web/core/assets";
import { onMounted, onPatched, onWillStart, onWillUnmount, signal } from "@odoo/owl";

/**
 * Manages the lifecycle of a Chart.js chart: loads the chart.js bundle before
 * the first render, instantiates the chart once the component is mounted and
 * re-instantiates it after each patch, destroying the previous instance every
 * time (and when the component is unmounted).
 *
 * @param {() => object} getConfig returns the Chart.js configuration
 * @returns {{ ref: () => HTMLCanvasElement, instance: () => Chart|null }} the signal
 *  ref to put on the canvas, and an accessor on the current chart instance
 */
export function useChart(getConfig) {
    const ref = signal.ref();
    let chart = null;

    function destroyChart() {
        if (chart) {
            chart.destroy();
            chart = null;
        }
    }

    function renderChart() {
        destroyChart();
        const canvas = ref();
        if (canvas) {
            chart = new Chart(canvas, getConfig());
        }
    }

    onWillStart(() => loadBundle("web.chartjs_lib"));
    onMounted(renderChart);
    onPatched(renderChart);
    onWillUnmount(destroyChart);

    return { ref, instance: () => chart };
}
