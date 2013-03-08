openerp.survey = function(openerp) {
    openerp.web_kanban.KanbanRecord.include({
        on_card_clicked: function() {
            if (this.view.dataset.model === 'survey') {
                this.$('.oe_kanban_survey_list .oe_survey_fill').first().click();
            } else {
                this._super.apply(this, arguments);
            }
        },
    });
};
