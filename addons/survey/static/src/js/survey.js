openerp.survey = function(openerp) {
    openerp.web_kanban.KanbanRecord.include({
        on_card_clicked: function(e) {
            if (this.view.dataset.model === 'survey') {
                this.$('.oe_survey_fill a:first').click();
            } else {
                this._super.apply(this, arguments);
            }
        },
    });
};
