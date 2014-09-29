openerp.crm_wardialing = function(instance) {
    instance.web_kanban.KanbanRecord.include({
        

        start: function() {
            var self = this;
            this._super.apply(this, arguments);
            if (this.view.dataset.model === 'crm.lead') {
                
                this.$el.find(".oe_dial_lead_to_call_center_button_icon").parent().click(function() {
                    console.log(self.view.dataset.get_context());
                    console.log(self.record.name.raw_value);
                    console.log(self);
                    openerp.client.action_manager.do_action({
                        type: 'ir.actions.act_window',
                        key2: 'client_action_multi',
                        src_model: "crm.lead",
                        res_model: "crm.wardialing.wizard",
                        multi: "True",
                        target: 'new',
                        context: {'opportunity_id': self.id},
                        views: [[false, 'form']],
                    });
                });
            }

        },

        


    });
};