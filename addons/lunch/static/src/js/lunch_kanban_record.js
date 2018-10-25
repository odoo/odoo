odoo.define('lunch.LunchKanbanRecord', function (require) {
"use strict";

/**
 * This file defines the KanbanRecord for the Lunch Kanban view.
 */

var KanbanRecord = require('web.KanbanRecord');

var LunchKanbanRecord = KanbanRecord.extend({
    _onGlobalClick: function (ev) {
        ev.preventDefault();
        // ignore clicks on oe_kanban_action elements
        if (!$(ev.target).hasClass('oe_kanban_action')) {
            this.trigger_up('open_wizard', {productId: this.recordData.product_id});
        }
    },
});

return LunchKanbanRecord;

});
