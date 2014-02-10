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
            var value = _.pluck(self.field.value, 'value');
            var tooltips = _.pluck(self.field.value, 'tooltip');
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
                    chartRangeMin: 0,
                    tooltipValueLookups: {
                        'offset': tooltips
                    }
                }, self.options);
            self.$el.sparkline(value, sparkline_options);
            self.$el.tipsy({'delayIn': self.options.delayIn || 0, 'html': true, 'title': function(){return title}, 'gravity': 'n'});
        }, 0);
    },
});

instance.web_kanban.fields_registry.add("sparkline_bar", "instance.web_kanban.SparklineBarWidget");


}
