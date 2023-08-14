odoo.define('web_kanban_gauge.widget', function (require) {
"use strict";

var AbstractField = require('web.AbstractField');
var core = require('web.core');
var field_registry = require('web.field_registry');
var utils = require('web.utils');

var _t = core._t;

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

var GaugeWidget = AbstractField.extend({
    className: "oe_gauge",
    jsLibs: [
        '/web/static/lib/Chart/Chart.js',
    ],

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     */
    _render: function () {
        // current value
        var val = this.value;
        if (_.isArray(JSON.parse(val))) {
            val = JSON.parse(val);
        }
        var gauge_value = _.isArray(val) && val.length ? val[val.length-1].value : val;
        if (this.nodeOptions.gauge_value_field) {
            gauge_value = this.recordData[this.nodeOptions.gauge_value_field];
        }

        // max_value
        var max_value = this.nodeOptions.max_value || 100;
        if (this.nodeOptions.max_field) {
            max_value = this.recordData[this.nodeOptions.max_field];
        }
        max_value = Math.max(gauge_value, max_value);

        // label
        var label = this.nodeOptions.label || "";
        if (this.nodeOptions.label_field) {
            label = this.recordData[this.nodeOptions.label_field];
        }

        // title
        var title = this.nodeOptions.title || this.field.string;

        var maxLabel = max_value;
        if (gauge_value === 0 && max_value === 0) {
            max_value = 1;
            maxLabel = 0;
        }
		var config = {
			type: 'doughnut',
			data: {
				datasets: [{
					data: [
                        gauge_value,
                        max_value - gauge_value
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
                        label: function(tooltipItems) {
                            if (tooltipItems.index === 0) {
                                return _t('Value: ') + gauge_value;
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
        this.$canvas = $('<canvas/>');
        this.$el.empty();
        this.$el.append(this.$canvas);
        this.$el.attr('style', this.nodeOptions.style);
        this.$el.css({position: 'relative'});
        var context = this.$canvas[0].getContext('2d');
        this.chart = new Chart(context, config);

        var humanValue = utils.human_number(gauge_value, 1);
        var $value = $('<span class="o_gauge_value">').text(humanValue);
        $value.css({'text-align': 'center', position: 'absolute', left: 0, right: 0, bottom: '6px', 'font-weight': 'bold'});
        this.$el.append($value);
    },
});

field_registry.add("gauge", GaugeWidget);

return GaugeWidget;

});
