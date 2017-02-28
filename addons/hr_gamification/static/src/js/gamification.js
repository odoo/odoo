odoo.define('hr_gamification.hr_gamification', function(require) {
"use strict";

var KanbanRecord = require('web.KanbanRecord');

KanbanRecord.include({
    on_card_clicked: function() {
        if (this.modelName === 'gamification.badge.user') {
            var action = {
                type: 'ir.actions.act_window',
                res_model: 'gamification.badge',
                view_mode: 'form',
                view_type: 'form,kanban,tree',
                views: [[false, 'form']],
                res_id: this.record.badge_id.raw_value[0]
            };
            this.do_action(action);
        } else {
            this._super.apply(this, arguments);
        }
    }
});

});
