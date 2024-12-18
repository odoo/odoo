import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { loadBundle } from "@web/core/assets";
import weUtils from "@web_editor/js/common/utils";

class Chart extends Interaction {

    static selector = ".s_chart";

    setup() {
        this.chart = null;
        this.style = window.getComputedStyle(document.documentElement);
    }

    async willStart() {
        await loadBundle("web.chartjs_lib");
    }

    start() {
        const data = JSON.parse(this.el.dataset.data);
        data.datasets.forEach(el => {
            if (Array.isArray(el.backgroundColor)) {
                el.backgroundColor = el.backgroundColor.map(el => this.convertToCSSColor(el));
                el.borderColor = el.borderColor.map(el => this.convertToCSSColor(el));
            } else {
                el.backgroundColor = this.convertToCSSColor(el.backgroundColor);
                el.borderColor = this.convertToCSSColor(el.borderColor);
            }
            el.borderWidth = this.el.dataset.borderWidth;
        });

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
                    if (label) {
                        if (secondLabel) {
                            final = label + " - " + secondLabel;
                        }
                    } else if (secondLabel) {
                        final = secondLabel;
                    }
                    return final + ":" + tooltipItem.formattedValue;
                },
            };
        }

        // Disable animation in edit mode
        if (this.editableMode) {
            chartData.options.animation = {
                duration: 0,
            };
        }

        const canvas = this.el.querySelector("canvas");
        window.Chart.Tooltip.positioners.custom = (elements, eventPosition) => eventPosition;
        this.chart = new window.Chart(canvas, chartData);
        this.registerCleanup(() => {
            this.chart.destroy();
            this.el.querySelectorAll(".chartjs-size-monitor").forEach(el => el.remove());
        });
    }

    /**
     * @param {string} color
     * @returns {string}
     */
    convertToCSSColor(color) {
        if (!color) {
            return "transparent";
        }
        return weUtils.getCSSVariableValue(color, this.style) || color;
    }
}

registry.category("public.interactions").add("website.chart", Chart);

registry
    .category("public.interactions.edit")
    .add("website.chart", {
        Interaction: Chart,
    });
