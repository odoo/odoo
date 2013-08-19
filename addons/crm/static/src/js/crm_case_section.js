openerp.crm = function(openerp) {
var _t = openerp.web._t;
    openerp.web_kanban.KanbanRecord.include({
        on_card_clicked: function() {
            if (this.view.dataset.model === 'crm.case.section') {
                this.$('.oe_kanban_crm_salesteams_list a').first().click();
            } else {
                this._super.apply(this, arguments);
            }
        },
    });
    openerp.crm.SparklineBarWidget = openerp.web_kanban.AbstractField.extend({
        className: "oe_sparkline_bar",
        start: function() {
            var self = this;
            var title = this.$node.html();
            setTimeout(function () {
                var value = _.pluck(self.field.value, 'value');
                var tooltips = _.pluck(self.field.value, 'tooltip');
                var currency_symbol = "";
                if (self.getParent()){
                    currency_symbol = self.getParent().record.currency_symbol.raw_value;
                };
                self.$el.sparkline(value, {
                    type: 'bar',
                    barWidth: 5,
                    tooltipFormat: _.str.sprintf("{{offset:offset}}: {{value}} %s",self.$el.closest("div[class='oe_salesteams_leads']").attr('class') ? _t('Lead(s)') : currency_symbol),
                    tooltipValueLookups: {
                        'offset': tooltips
                    },
                });
                self.$el.tipsy({'delayIn': 3000, 'html': true, 'title': function(){return title}, 'gravity': 'n'});
            }, 0);
        },
    });
    openerp.web_kanban.fields_registry.add("sparkline_bar", "openerp.crm.SparklineBarWidget");

};
