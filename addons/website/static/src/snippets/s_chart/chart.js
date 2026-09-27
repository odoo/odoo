import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { getCSSVariableValue } from "@html_editor/utils/formatting";
import { loadBundle } from "@web/core/assets";
import { convertCSSColorToRgba } from "@web/core/utils/colors";

export class Chart extends Interaction {
    static selector = ".s_chart";

    setup() {
        this.chart = null;
        this.noAnimation = false;
        this.style = window.getComputedStyle(document.documentElement);
        this.chartBlockStyle = window.getComputedStyle(this.el);
    }

    async willStart() {
        await loadBundle("web.chartjs_lib");
    }

    start() {
        const data = JSON.parse(this.el.dataset.data);
        data.datasets.forEach((el) => {
            el.backgroundColor = this.convertToCSS(el.backgroundColor);
            el.borderColor = this.convertToCSS(el.borderColor);
            el.borderWidth = this.el.dataset.borderWidth;
            el.color = this.convertToCSS(el.color);
        });

        const colorRgba = convertCSSColorToRgba(this.chartBlockStyle.color);
        const textColor = `rgba(${colorRgba.red}, ${colorRgba.green}, ${colorRgba.blue}, ${colorRgba.opacity})`;
        const cartesianColor = `rgba(${colorRgba.red}, ${colorRgba.green}, ${colorRgba.blue}, 0.25)`;

        const radialAxis = {
            beginAtZero: true,
        };

        const linearAxis = {
            type: "linear",
            stacked: this.el.dataset.stacked === "true",
            beginAtZero: true,
            min: parseInt(this.el.dataset.ticksMin),
            max: parseInt(this.el.dataset.ticksMax),
            grid: {
                color: cartesianColor,
            },
            ticks: {
                color: textColor,
            },
        };

        const categoryAxis = {
            type: "category",
            stacked: this.el.dataset.stacked === "true",
            grid: {
                color: cartesianColor,
            },
            ticks: {
                color: textColor,
            },
        };

        const chartData = {
            type: this.el.dataset.type,
            data: data,
            options: {
                plugins: {
                    legend: {
                        display: this.el.dataset.legendPosition !== "none",
                        position: this.el.dataset.legendPosition,
                        labels: {
                            color: textColor,
                        },
                    },
                    tooltip: {
                        enabled: this.el.dataset.tooltipDisplay === "true",
                        position: "custom",
                    },
                    title: {
                        display: !!this.el.dataset.title,
                        text: this.el.dataset.title,
                        color: textColor,
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

        if (this.noAnimation) {
            chartData.options.animation = { duration: 0 };
        }

        const canvasEl = this.el.querySelector("canvas");
        window.Chart.Tooltip.positioners.custom = (_, eventPosition) => eventPosition;
        this.chart = new window.Chart(canvasEl, chartData);
        this.registerCleanup(() => {
            this.chart.destroy();
            this.el.querySelectorAll(".chartjs-size-monitor").forEach((el) => el.remove());
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
