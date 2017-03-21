odoo.define('sales_team.update_kanban', function (require) {
"use strict";

var KanbanRecord = require('web.KanbanRecord');

KanbanRecord.include({
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     */
    _openRecord: function () {
        if (this.modelName === 'crm.team') {
            this.$('.oe_kanban_crm_salesteams_list a').first().click();
        } else {
            this._super.apply(this, arguments);
        }
    },
});
});
