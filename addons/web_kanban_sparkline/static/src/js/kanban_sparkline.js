odoo.define('web_kanban_sparkline.widget', function (require) {
"use strict";

var kanban_common = require('web_kanban.common');

var AbstractField = kanban_common.AbstractField;
var fields_registry = kanban_common.registry;

/**
 * Kanban widgets: Sparkline
 *
 */

var SparklineBarWidget = AbstractField.extend({
    className: "oe_sparkline_bar",
    start: function() {
        var self = this;
        var title = this.$node.html() || this.field.string;
        setTimeout(function () {
            var tooltipFormatter =  function(sp, options, fields) {
                var format =  $.spformat('<div class="jqsfield">{{offset:offset}} {{formatted_value}}</div>');
                var result = '';
                $.each(fields, function(i, field) {
                        field.formatted_value = instance.web.format_value(field.value, { type : 'float' });
                        result += format.render(field, options.get('tooltipValueLookups'), options);
                })
                return result;
            }
            var field_value = JSON.parse(self.field.value);
            var value = _.pluck(field_value, 'value');
            var tooltips = _.pluck(field_value, 'tooltip');
            var suffix = self.options.tooltip_suffix || "";
            var tooltipFormat = self.options.type == 'tristate' && '{{offset:offset}}' + suffix || '{{offset:offset}} {{value:value}}' + suffix;
            var sparkline_options = _.extend({
                    type: 'bar',
                    height: '20px',
                    barWidth: 4,
                    barSpacing: 1,
                    barColor: '#96d854',
                    tooltipFormat: tooltipFormat,
                    tooltipFormatter: self.options.type == 'tristate' ? undefined : tooltipFormatter,
                    chartRangeMin: 0,
                    tooltipValueLookups: {
                        'offset': tooltips
                    }
                }, self.options);
            self.$el.sparkline(value, sparkline_options);
            self.$el.tooltip({delay: {show: self.options.delayIn || 0, hide: 0}, title: function(){return title;}});
        }, 0);
    },
});

fields_registry.add("sparkline_bar", SparklineBarWidget);


});
