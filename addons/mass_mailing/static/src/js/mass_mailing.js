openerp.mass_mailing = function(openerp) {

    openerp.web_kanban.KanbanRecord.include({
        on_card_clicked: function (event) {
            if (this.view.dataset.model === 'mail.mass_mailing.campaign') {
                this.$('.oe_mass_mailings a').first().click();
            } else {
                this._super.apply(this, arguments);
            }
        },
    });

};
