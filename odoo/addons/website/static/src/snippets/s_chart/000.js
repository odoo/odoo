/** @odoo-module **/

import { loadBundle } from "@web/core/assets";
import publicWidget from "@web/legacy/js/public/public_widget";
import weUtils from "@web_editor/js/common/utils";

const ChartWidget = publicWidget.Widget.extend({
    selector: '.s_chart',
    disabledInEditableMode: false,

    /**
     * @override
     * @param {Object} parent
     * @param {Object} options The default value of the chartbar.
     */
    init: function (parent, options) {
        this._super.apply(this, arguments);
        this.style = window.getComputedStyle(document.documentElement);
    },
    /**
     * @override
     */
    start: function () {
        // Convert Theme colors to css color
        const data = JSON.parse(this.el.dataset.data);
        data.datasets.forEach(el => {
            if (Array.isArray(el.backgroundColor)) {
                el.backgroundColor = el.backgroundColor.map(el => this._convertToCssColor(el));
                el.borderColor = el.borderColor.map(el => this._convertToCssColor(el));
            } else {
                el.backgroundColor = this._convertToCssColor(el.backgroundColor);
                el.borderColor = this._convertToCssColor(el.borderColor);
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
            stacked: this.el.dataset.stacked === "true",
        };

        // Make chart data
        const chartData = {
            type: this.el.dataset.type,
            data: data,
            options: {
                plugins: {
                    legend: {
                        display: this.el.dataset.legendPosition !== 'none',
                        position: this.el.dataset.legendPosition,
                    },
                    tooltip: {
                        enabled: this.el.dataset.tooltipDisplay === 'true',
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

        // Add type specific options
        if (this.el.dataset.type === 'radar') {
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
        } else if (['pie', 'doughnut'].includes(this.el.dataset.type)) {
            chartData.options.scales = {};
            chartData.options.plugins.tooltip.callbacks = {
                label: (tooltipItem) => {
                    const label = tooltipItem.label;
                    const secondLabel = tooltipItem.dataset.label;
                    let final = label;
                    if (label) {
                        if (secondLabel) {
                            final = label + ' - ' + secondLabel;
                        }
                    } else if (secondLabel) {
                        final = secondLabel;
                    }
                    return final + ':' + tooltipItem.formattedValue;
                },
            };
        }

        // Disable animation in edit mode
        if (this.editableMode) {
            chartData.options.animation = {
                duration: 0,
            };
        }

        const canvas = this.el.querySelector('canvas');
        window.Chart.Tooltip.positioners.custom = (elements, eventPosition) => eventPosition;
        this.chart = new window.Chart(canvas, chartData);
        return this._super.apply(this, arguments);
    },

    willStart: async function () {
        await loadBundle("web.chartjs_lib");
    },
    /**
     * @override
     * Discard all library changes to reset the state of the Html.
     */
    destroy: function () {
        if (this.chart) { // The widget can be destroyed before start has completed
            this.chart.destroy();
            this.el.querySelectorAll('.chartjs-size-monitor').forEach(el => el.remove());
        }
        this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {string} color A css color or theme color string
     * @returns {string} Css color
     */
    _convertToCssColor: function (color) {
        if (!color) {
            return 'transparent';
        }
        return weUtils.getCSSVariableValue(color, this.style) || color;
    },
});

publicWidget.registry.chart = ChartWidget;

export default ChartWidget;
