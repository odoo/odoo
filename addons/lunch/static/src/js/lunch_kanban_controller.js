odoo.define('lunch.LunchKanbanController', function (require) {
"use strict";

/**
 * This file defines the Controller for the Lunch Kanban view, which is an
 * override of the KanbanController.
 */

var KanbanController = require('web.KanbanController');
var LunchControllerCommon = require('lunch.LunchControllerCommon');

var LunchKanbanController = KanbanController.extend(LunchControllerCommon , {
    custom_events: _.extend({}, KanbanController.prototype.custom_events, LunchControllerCommon.custom_events),
});

return LunchKanbanController;

});
