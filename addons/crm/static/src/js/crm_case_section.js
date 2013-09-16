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

    openerp.web_kanban.SparklineBarWidgetSalesTeam = openerp.web_kanban.SparklineBarWidget.extend({
        set_offset:function(){
            var self = this;
            var currency_symbol = "";
            if (self.getParent()){
                currency_symbol = self.getParent().record.currency_symbol.raw_value;
            };
            return _.str.sprintf("{{offset:offset}}: {{value}} %s",self.$el.closest("div[class='oe_salesteams_leads']").attr('class') ? _t('Lead(s)') : currency_symbol)
        }
    });

openerp.web_kanban.fields_registry.add("sparkline_bar_sales", "openerp.web_kanban.SparklineBarWidgetSalesTeam");
};
