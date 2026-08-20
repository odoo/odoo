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
        this.type = this.el.dataset.type;
        this.fontSize = parseInt(this.el.dataset.fontSize) || 12;
        this.borderWidth = parseInt(this.el.dataset.borderWidth) || 2;
        this.isInterpolated = this.type === "line" && this.el.dataset.interpolate === "true";
        this.isPieStyle = ["pie", "doughnut"].includes(this.type);
        this.isPointStyle = ["line", "radar"].includes(this.type);
    }

    async willStart() {
        await loadBundle("web.chartjs_lib");
    }

    start() {
        const data = JSON.parse(this.el.dataset.data);

        for (const dataset of data.datasets) {
            dataset.backgroundColor = this.convertToCSS(dataset.backgroundColor);
            dataset.borderColor = this.convertToCSS(dataset.borderColor);
            dataset.borderWidth = this.borderWidth;
            dataset.color = this.convertToCSS(dataset.color);

            if (this.isPointStyle) {
                dataset.radius = this.borderWidth;
                dataset.hitRadius = Math.max(this.borderWidth, 6);
                dataset.hoverRadius = this.borderWidth * 1.25;
                dataset.hoverBorderWidth = this.borderWidth * 1.25;
                dataset.cubicInterpolationMode = this.isInterpolated ? "monotone" : "default";
            }
        }

        const colorRgba = convertCSSColorToRgba(this.chartBlockStyle.color);
        const textColor = `rgba(${colorRgba.red}, ${colorRgba.green}, ${colorRgba.blue}, ${colorRgba.opacity})`;
        const luminance =
            colorRgba.red * 0.2126 + colorRgba.green * 0.7152 + colorRgba.blue * 0.0722;
        const isLightText = luminance > 255 / 2;
        const tooltipColor = isLightText ? "#000000cc" : "#ffffffcc";
        const cartesianColor = `rgba(${colorRgba.red}, ${colorRgba.green}, ${colorRgba.blue}, 0.25)`;

        // Only use the fallback value when no value is defined to accept 0,
        // which would otherwise be falsy.
        function parseChartFloat(value, fallback) {
            const parsedValue = parseInt(value);
            return isNaN(parsedValue) ? fallback : parsedValue;
        }

        const ticksMin = parseChartFloat(this.el.dataset.ticksMin);
        const ticksMax = parseChartFloat(this.el.dataset.ticksMax);

        const radialAxis = {
            beginAtZero: true,
            max: ticksMax,
            pointLabels: { color: textColor, font: { size: this.fontSize } },
            grid: {
                color: cartesianColor,
            },
            ticks: {
                font: { size: this.fontSize },
            },
        };

        const linearAxis = {
            type: "linear",
            stacked: this.el.dataset.stacked === "true",
            beginAtZero: true,
            min: ticksMin,
            max: ticksMax,
            grid: {
                color: cartesianColor,
            },
            ticks: {
                color: textColor,
                font: { size: this.fontSize },
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
                font: { size: this.fontSize },
            },
        };

        const chartData = {
            type: this.type,
            data: data,
            options: {
                plugins: {
                    legend: {
                        display: this.el.dataset.legendPosition !== "none",
                        position: this.el.dataset.legendPosition,
                        labels: {
                            color: textColor,
                            font: { size: this.fontSize },
                            boxWidth: this.fontSize * 2.5,
                            boxHeight: this.fontSize,
                            usePointStyle: this.isPointStyle,
                        },
                    },
                    tooltip: {
                        enabled: this.el.dataset.tooltipDisplay === "true",
                        position: "custom",
                        titleColor: tooltipColor,
                        titleFont: { size: this.fontSize },
                        bodyColor: tooltipColor,
                        bodyFont: { size: this.fontSize },
                        boxWidth: this.fontSize,
                        boxHeight: this.fontSize,
                        boxPadding: 2,
                        usePointStyle: this.isPointStyle,
                        backgroundColor: isLightText ? "white" : "black",
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

        if (this.type === "radar") {
            chartData.options.scales = {
                r: radialAxis,
            };
        } else if (this.type === "horizontalBar") {
            chartData.type = "bar";
            chartData.options.scales = {
                x: linearAxis,
                y: categoryAxis,
            };
            chartData.options.indexAxis = "y";
        } else if (this.isPieStyle) {
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
