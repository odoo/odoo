odoo.define('mass_mailing.mass_mailing', function (require) {
"use strict";

var KanbanRecord = require('web.KanbanRecord');
var KanbanColumn = require('web.KanbanColumn');

KanbanRecord.include({
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     */
    _openRecord: function () {
        if (this.modelName === 'mail.mass_mailing.campaign') {
            this.$('.oe_mailings').click();
        } else if (this.modelName === 'mail.mass_mailing.list' &&
            this.$('.o_mailing_list_kanban_boxes a')) {
            this.$('.o_mailing_list_kanban_boxes a').first().click();
        } else {
            this._super.apply(this, arguments);
        }
    },
});

KanbanColumn.include({
    init: function () {
        this._super.apply(this, arguments);
        if (this.modelName === 'mail.mass_mailing') {
            this.draggable = false;
        }
    },
});

});
