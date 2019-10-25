odoo.define('hr_timesheet.timesheet_kanban_view', function (require) {
"use strict";

const KanbanController = require('web.KanbanController');
const KanbanView = require('web.KanbanView');
const viewRegistry = require('web.view_registry');

/**
 * @override the KanbanController to add a trigger when a timer is launched or stopped
 */
const TimesheetKanbanController = KanbanController.extend({
    custom_events: _.extend({}, KanbanController.prototype.custom_events, {
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

const TimesheetKanbanView = KanbanView.extend({
    config: _.extend({}, KanbanView.prototype.config, {
        Controller: TimesheetKanbanController
    })
});

viewRegistry.add('timesheet_kanban_view', TimesheetKanbanView);

return { TimesheetKanbanController, TimesheetKanbanView };

});
