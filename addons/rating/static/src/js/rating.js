odoo.define('rating.kanban', function(require) {
"use strict";

var KanbanRecord = require('web_kanban.Record');

KanbanRecord.include({
    on_card_clicked: function() {
        if (this.model === 'rating.rating') {
            this.$('a').first().click();
        } else {
            this._super.apply(this, arguments);
        }
    },
});

});
