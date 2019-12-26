odoo.define('hr_timesheet.timesheet_list_view', function (require) {
"use strict";

const ListController = require('web.ListController');
var ListView = require('web.ListView');
var viewRegistry = require('web.view_registry');

/**
 * @override the ListController to add a trigger when the timer is launched or stopped
 */
const TimesheetListController = ListController.extend({
    custom_events: _.extend({}, ListController.prototype.custom_events, {
        'timer_changed': '_onTimerChanged',
    }),
    /**
     * When a timer is launched or stopped, we reload the view to see the updating.
     * @param {Object} event
     */
    _onTimerChanged: function (event) {
        this.reload();
    }
});

const TimesheetListView = ListView.extend({
    config: _.extend({}, ListView.prototype.config, {
        Controller: TimesheetListController
    })
});

viewRegistry.add('timesheet_tree', TimesheetListView);

return { TimesheetListController, TimesheetListView };

});
