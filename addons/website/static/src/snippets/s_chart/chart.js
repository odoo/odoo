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
        this.fontSize = parseInt(this.el.dataset.fontSize) || 12;
        this.borderWidth = parseInt(this.el.dataset.borderWidth);
        this.isLineStyle = this.el.dataset.type === "line";
        this.isPieStyle = ["pie", "doughnut"].includes(this.el.dataset.type);
        this.isPointStyle = ["line", "radar"].includes(this.el.dataset.type);
    }

    async willStart() {
        await loadBundle("web.chartjs_lib");
    }

    start() {
        const data = JSON.parse(this.el.dataset.data);

        const pointStyle = (el) => {
            el.radius = this.borderWidth;
            el.hitRadius = Math.max(this.borderWidth, 6);
            el.hoverRadius = this.borderWidth * 1.25;
            el.hoverBorderWidth = this.borderWidth * 1.25;
            el.cubicInterpolationMode = el.interpolate && this.isLineStyle ? "monotone" : "default";
        };

        const defaultStyle = (el) => {
            el.backgroundColor = this.convertToCSS(el.backgroundColor);
            el.borderColor = this.convertToCSS(el.borderColor);
            el.borderWidth = this.borderWidth;
            el.color = this.convertToCSS(el.color);
        };

        if (this.isPointStyle) {
            data.datasets.forEach((el) => ({ ...defaultStyle(el), ...pointStyle(el) }));
        } else {
            data.datasets.forEach((el) => defaultStyle(el));
        }

        const colorRgba = convertCSSColorToRgba(this.chartBlockStyle.color);
        const textColor = `rgba(${colorRgba.red}, ${colorRgba.green}, ${colorRgba.blue}, ${colorRgba.opacity})`;
        const luminance =
            colorRgba.red * 0.2126 + colorRgba.green * 0.7152 + colorRgba.blue * 0.072;
        const tooltipDarkmode = luminance > 255 / 2;
        const cartesianColor = `rgba(${colorRgba.red}, ${colorRgba.green}, ${colorRgba.blue}, 0.25)`;

        const radialAxis = {
            beginAtZero: true,
            max: parseInt(this.el.dataset.ticksMax) || undefined,
            pointLabels: { font: { size: this.fontSize } },
        };

        const linearAxis = {
            type: "linear",
            stacked: this.el.dataset.stacked === "true",
            beginAtZero: true,
            min: parseInt(this.el.dataset.ticksMin) || undefined,
            max: parseInt(this.el.dataset.ticksMax) || undefined,
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
            type: this.el.dataset.type,
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
                            usePointStyle: this.isLineStyle || this.isRadarStyle,
                        },
                    },
                    tooltip: {
                        enabled: this.el.dataset.tooltipDisplay === "true",
                        position: "custom",
                        titleColor: tooltipDarkmode ? "#000000cc" : "#ffffffcc",
                        titleFont: { size: this.fontSize },
                        bodyColor: tooltipDarkmode ? "#000000cc" : "#ffffffcc",
                        bodyFont: { size: this.fontSize },
                        boxWidth: this.fontSize,
                        boxHeight: this.fontSize,
                        boxPadding: 2,
                        usePointStyle: this.isLineStyle || this.isRadarStyle,
                        backgroundColor: tooltipDarkmode ? "white" : "black",
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
