openerp.mass_mailing = function (instance) {
    var _t = instance.web._t;

    openerp.web_kanban.KanbanRecord.include({
        on_card_clicked: function (event) {
            if (this.view.dataset.model === 'mail.mass_mailing.campaign') {
                this.$('.oe_mailings').click();
            } else {
                this._super.apply(this, arguments);
            }
        },
    });

    openerp.web_kanban.KanbanView.include({
        on_groups_started: function() {
            this._super.apply(this, arguments);
            if (this.dataset.model === 'mail.mass_mailing') {  
                this.$el.find('.oe_kanban_draghandle').removeClass('oe_kanban_draghandle');
            }
        },
    });
};
