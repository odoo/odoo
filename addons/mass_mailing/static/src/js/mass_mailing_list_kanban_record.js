odoo.define('mass_mailing.ListKanbanRecord', function (require) {
"use strict";

var KanbanRecord = require('web.KanbanRecord');

var MassMailingListKanbanRecord = KanbanRecord.extend({
    /**
     * @override
     * @private
     */
    _openRecord: function () {
        this.$('.o_mailing_list_kanban_boxes a').first().click();
    }
});

return MassMailingListKanbanRecord;

});
