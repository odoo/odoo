odoo.define('hr_recruitment.hr_recruitment', ['web_kanban.common'], function(require) {
"use strict";

var common = require('web_kanban.common');

common.KanbanRecord.include({
    on_card_clicked: function() {
        if (this.view.dataset.model === 'hr.job') {
            this.$('.oe_applications a').first().click();
        } else {
            this._super.apply(this, arguments);
        }
    },
});

});
