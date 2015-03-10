odoo.define('hr.hr', ['web_kanban.common'], function(require) {
"use strict";

var common = require('web_kanban.common');

common.KanbanRecord.include({
    on_card_clicked: function() {
        if (this.view.dataset.model === 'hr.department') {
            this.$('.oe_kanban_department .oe_kanban_content a').first().click();
        } else {
            this._super.apply(this, arguments);
        }
    },
});


});

