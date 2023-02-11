odoo.define('lunch.LunchKanbanRenderer', function (require) {
"use strict";

/**
 * This file defines the Renderer for the Lunch Kanban view, which is an
 * override of the KanbanRenderer.
 */

var LunchKanbanRecord = require('lunch.LunchKanbanRecord');

var KanbanRenderer = require('web.KanbanRenderer');

var LunchKanbanRenderer = KanbanRenderer.extend({
    config: _.extend({}, KanbanRenderer.prototype.config, {
        KanbanRecord: LunchKanbanRecord,
    }),

    /**
     * @override
     */
    start: function () {
        this.$el.addClass('o_lunch_view o_lunch_kanban_view position-relative align-content-start flex-grow-1 flex-shrink-1');
        return this._super.apply(this, arguments);
    },
});

return LunchKanbanRenderer;

});
