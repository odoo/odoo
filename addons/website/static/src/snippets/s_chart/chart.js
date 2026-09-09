/** @odoo-module native */
import { getCSSVariableValue } from "@html_editor/utils/formatting";
import { makeLogger } from "@web/core/debug/debug_logger";
import { Chart as ChartJS, loadChartJS, Tooltip } from "@web/core/lib/chartjs";
import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";

const log = makeLogger("website.snippet.s_chart");
export class Chart extends Interaction {
    static selector = ".s_chart";

    setup() {
        this.chart = null;
        this.noAnimation = false;
        this.style = window.getComputedStyle(document.documentElement);
    }

    async willStart() {
        const endLoadChartJs = log.perf("willStart loadChartJS");
        await loadChartJS();
        endLoadChartJs();
    }

    start() {
        const endParse = log.perf("start parse data and convert colors");
        let data;
        try {
            data = JSON.parse(this.el.dataset.data);
        } catch {
            endParse();
            return;
        }
        data.datasets.forEach((el) => {
            el.backgroundColor = this.convertToCSS(el.backgroundColor);
            el.borderColor = this.convertToCSS(el.borderColor);
            el.borderWidth = this.el.dataset.borderWidth;
        });

        endParse(() => ({
            datasets: data.datasets.length,
            labels: data.labels?.length,
        }));

        const radialAxis = {
            beginAtZero: true,
        };

        const linearAxis = {
            type: "linear",
            stacked: this.el.dataset.stacked === "true",
            beginAtZero: true,
            min: parseInt(this.el.dataset.ticksMin),
            max: parseInt(this.el.dataset.ticksMax),
        };

        const categoryAxis = {
            type: "category",
            stacked: this.el.dataset.stacked === "true",
        };

        const chartData = {
            type: this.el.dataset.type,
            data: data,
            options: {
                plugins: {
                    legend: {
                        display: this.el.dataset.legendPosition !== "none",
                        position: this.el.dataset.legendPosition,
                    },
                    tooltip: {
                        enabled: this.el.dataset.tooltipDisplay === "true",
                        position: "custom",
                    },
                    title: {
                        display: !!this.el.dataset.title,
                        text: this.el.dataset.title,
                    },
                },
                scales: {
                    x: categoryAxis,
                    y: linearAxis,
                },
                aspectRatio: 2,
            },
        };

        if (this.el.dataset.type === "radar") {
            chartData.options.scales = {
                r: radialAxis,
            };
        } else if (this.el.dataset.type === "horizontalBar") {
            chartData.type = "bar";
            chartData.options.scales = {
                x: linearAxis,
                y: categoryAxis,
            };
            chartData.options.indexAxis = "y";
        } else if (["pie", "doughnut"].includes(this.el.dataset.type)) {
            chartData.options.scales = {};
            chartData.options.plugins.tooltip.callbacks = {
                label: (tooltipItem) => {
                    const label = tooltipItem.label;
                    const secondLabel = tooltipItem.dataset.label;
                    let final = label;
                    if (label && secondLabel) {
                        final = label + " - " + secondLabel;
                    } else if (secondLabel) {
                        final = secondLabel;
                    }
                    return final + ":" + tooltipItem.formattedValue;
                },
            };
        }

        log.logic("start: chart type resolved", () => ({
            type: this.el.dataset.type,
            resolvedType: chartData.type,
            scales: Object.keys(chartData.options.scales),
            noAnimation: this.noAnimation,
        }));
        if (this.noAnimation) {
            chartData.options.animation = { duration: 0 };
        }

        const canvasEl = this.el.querySelector("canvas");
        Tooltip.positioners.custom = (_, eventPosition) => eventPosition;
        const endCreate = log.perf("start new ChartJS");
        this.chart = new ChartJS(canvasEl, chartData);
        endCreate();
        this.registerCleanup(() => {
            log.lifecycle("cleanup: chart destroyed");
            this.chart.destroy();
            this.el
                .querySelectorAll(".chartjs-size-monitor")
                .forEach((el) => el.remove());
        });
    }

    /**
     * @param {Array[string] || string} paramColor
     */
    convertToCSS(paramColor) {
        return Array.isArray(paramColor)
            ? paramColor.map((color) => this.convertToCSSColor(color))
            : this.convertToCSSColor(paramColor);
    }

    /**
     * @param {string} color
     */
    convertToCSSColor(color) {
        return color ? getCSSVariableValue(color, this.style) || color : "transparent";
    }
}

registry.category("public.interactions").add("website.chart", Chart);
