openerp.stock = function(openerp) {

    openerp.stock.SparklineBarWidget = openerp.web_kanban.AbstractField.extend({
        className: "oe_sparkline_bar",
        start: function() {
            var self = this;
            var title = this.$node.html();
            setTimeout(function () {
                var value = _.pluck(self.field.value, 'value');
                var tooltips = _.pluck(self.field.value, 'tooltip');
		var type = this.options ? this.options.type : "bar";
                self.$el.sparkline(value, {
                    type: type,
                    barWidth: 5,
                    tooltipFormat: '{{offset:offset}}: {{value}} Move(s)',
                    tooltipValueLookups: {
                        'offset': tooltips
                    },
                });
                self.$el.tipsy({'delayIn': 3000, 'html': true, 'title': function(){return title}, 'gravity': 'n'});
            }, 0);
        },
    });

    openerp.stock.GaugeWidget = openerp.web_kanban.AbstractField.extend({
        className: "oe_gage",
        start: function() {
            var self = this;

            var parent = this.getParent();
            var max = 100;
            var label = this.options.label_field ? parent.record[this.options.label_field].raw_value : "";
            var title = this.$node.html();
            var val = this.field.value;
            var value = _.isArray(val) && val.length ? val[val.length-1]['value'] : val;
            var unique_id = _.uniqueId("JustGage");

            this.$el.empty()
                .attr('style', this.$node.attr('style') + ';position:relative; display:inline-block;')
                .attr('id', unique_id);
            this.gage = new JustGage({
                id: unique_id,
                node: this.$el[0],
                title: title,
                value: value,
                min: 0,
                max: max,
                relativeGaugeSize: true,
                humanFriendly: true,
                titleFontColor: '#333333',
                valueFontColor: '#333333',
                labelFontColor: '#000',
                label: label,
                levelColors: [
                    "#a9d70b",
                    "#f9c802",
                    "#ff0000"
                ],
            });
        },
    });

    openerp.web_kanban.fields_registry.add("stock_sparkline", "openerp.stock.SparklineBarWidget");
    openerp.web_kanban.fields_registry.add("stock_gage", "openerp.stock.GaugeWidget");

    openerp.stock = openerp.stock || {};
    openerp_picking_widgets(openerp);
    openerp.web.client_actions.add('stock.ui', 'instance.stock.PickingMainWidget');

};
