odoo.define('rating.kanban', function(require) {
"use strict";

var common = require('web_kanban.common');

common.KanbanRecord.include({
    on_card_clicked: function() {
        if (this.view.dataset.model === 'rating.rating') {
            this.$('a').first().click();
        } else {
            this._super.apply(this, arguments);
        }
    },
});

});
