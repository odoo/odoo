
openerp.rating = function(openerp) {
    "use strict";

    openerp.web_kanban.KanbanRecord.include({
        on_card_clicked: function(ev) {
            if (this.view.dataset.model === 'rating.rating') {
                this.$('a').first().click();
            } else {
                this._super.apply(this, arguments);
            }
        },
    });
};
