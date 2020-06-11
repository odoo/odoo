odoo.define('web_kanban_gauge.widget', function (require) {
"use strict";

const AbstractFieldOwl = require('web.AbstractFieldOwl');
const core = require('web.core');
const fieldRegistryOwl = require('web.field_registry_owl');
const utils = require('web.utils');

const { xml } = owl.tags;

const _t = core._t;
/**
 * options
 *
 * - max_value: maximum value of the gauge [default: 100]
 * - max_field: get the max_value from the field that must be present in the
 *   view; takes over max_value
 * - gauge_value_field: if set, the value displayed below the gauge is taken
 *   from this field instead of the base field used for
 *   the gauge. This allows to display a number different
 *   from the gauge.
 * - label: lable of the gauge, displayed below the gauge value
 * - label_field: get the label from the field that must be present in the
 *   view; takes over label
 * - title: title of the gauge, displayed on top of the gauge
 * - style: custom style
 */

class GaugeWidget extends AbstractFieldOwl {

    async willStart() {
        await owl.utils.loadJS("/web/static/lib/Chart/Chart.js");
    }

    mounted() {
        // current value
        let val = this.value;
        if (Array.isArray(JSON.parse(val))) {
            val = JSON.parse(val);
        }
        let gaugeValue = Array.isArray(val) && val.length ? val[val.length - 1].value : val;
        if (this.nodeOptions.gauge_value_field) {
            gaugeValue = this.recordData[this.nodeOptions.gauge_value_field];
        }

        // max_value
        let maxValue = this.nodeOptions.max_value || 100;
        if (this.nodeOptions.max_field) {
            maxValue = this.recordData[this.nodeOptions.max_field];
        }
        maxValue = Math.max(gaugeValue, maxValue);

        // title
        const title = this.nodeOptions.title || this.field.string;

        let maxLabel = maxValue;
        if (gaugeValue === 0 && maxValue === 0) {
            maxValue = 1;
            maxLabel = 0;
        }
        const config = {
            type: 'doughnut',
            data: {
                datasets: [{
                    data: [
                        gaugeValue,
                        maxValue - gaugeValue
                    ],
                    backgroundColor: [
                        "#1f77b4", "#dddddd"
                    ],
                    label: title
                }],
            },
            options: {
                circumference: Math.PI,
                rotation: -Math.PI,
                responsive: true,
                tooltips: {
                    displayColors: false,
                    callbacks: {
                        label: function (tooltipItems) {
                            if (tooltipItems.index === 0) {
                                return _t('Value: ') + gaugeValue;
                            }
                            return _t('Max: ') + maxLabel;
                        },
                    },
                },
                title: {
                    display: true,
                    text: title,
                    padding: 4,
                },
                layout: {
                    padding: {
                        bottom: 5
                    }
                },
                maintainAspectRatio: false,
                cutoutPercentage: 70,
            }
        };

        this.canvas = document.createElement("canvas");
        this.el.innerHTML = '';
        this.el.append(this.canvas);
        this.el.style = this.nodeOptions.style;
        this.el.style.position = 'relative';
        const context = this.canvas.getContext('2d');
        this.chart = new Chart(context, config);

        const humanValue = utils.human_number(gaugeValue, 1);
        const value = document.createElement('span');
        value.classList.add('o_gauge_value');
        value.textContent = humanValue;
        Object.assign(value.style, {'text-align': 'center', position: 'absolute', left: 0, right: 0, bottom: '6px', 'font-weight': 'bold'});
        this.el.append(value);
    }
};

GaugeWidget.template = xml`<div class="oe_gauge"/>`;

fieldRegistryOwl.add("gauge", GaugeWidget);

return GaugeWidget;

});
