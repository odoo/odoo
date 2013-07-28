openerp.stock = function(openerp) {
    openerp.stock.SparklineBarWidget = openerp.web_kanban.AbstractField.extend({
        className: "oe_sparkline_bar",
        start: function() {
            var self = this;
            var title = this.$node.html();
            setTimeout(function () {
                var value = _.pluck(self.field.value, 'value');
                var tooltips = _.pluck(self.field.value, 'tooltip');
                self.$el.sparkline(value, {
                    type: 'bar',
                    barWidth: 5,
                    tooltipFormat: '{{offset:offset}} {{value}}',
                    tooltipValueLookups: {
                        'offset': tooltips
                    },
                });
                self.$el.tipsy({'delayIn': 0, 'html': true, 'title': function(){return title}, 'gravity': 'n'});
            }, 0);
        },
    });
    openerp.web_kanban.fields_registry.add("stock_sparkline_bar", "openerp.stock.SparklineBarWidget");

};
