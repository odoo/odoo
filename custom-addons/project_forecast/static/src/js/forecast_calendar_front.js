/** @odoo-module **/

import PlanningView from '@planning/js/planning_calendar_front';

PlanningView.include({
        // override popup of calendar
        eventFunction: function (calEvent) {
            this._super.apply(this, arguments);
            const $project = $("#project");
            if (calEvent.event.extendedProps.project) {
                $project.text(calEvent.event.extendedProps.project);
                $project.css("display", "");
                $project.prev().css("display", "");
            } else {
                $project.css("display", "none");
                $project.prev().css("display", "none");
            }
            const $task = $("#task");
            if (calEvent.event.extendedProps.task) {
                $task.text(calEvent.event.extendedProps.task);
                $task.prev().css("display", "");
                $task.css("display", "");
            } else {
                $task.css("display", "none");
                $task.prev().css("display", "none");
            }
        },
    });
