openerp.web_kanban_sparkline = function (instance) {

/**
 * Kanban widgets: Sparkline
 *
 */

instance.web_kanban.SparklineBarWidget = instance.web_kanban.AbstractField.extend({
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
            var tooltipFormat = self.options.type == 'tristate' && '{{offset:offset}}' + suffix || '{{offset:offset}} {{value:value}}' + suffix
            var sparkline_options = _.extend({
                    type: 'bar',
                    barWidth: 5,
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
            self.$el.tooltip({delay: {show: self.options.delayIn || 0, hide: 0}, title: function(){return title}});
        }, 0);
    },
});

instance.web_kanban.fields_registry.add("sparkline_bar", "instance.web_kanban.SparklineBarWidget");


}
