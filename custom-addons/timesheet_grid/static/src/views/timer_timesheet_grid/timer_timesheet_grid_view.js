/** @odoo-module */

import { registry } from "@web/core/registry";

import { timesheetGridView } from "../timesheet_grid/timesheet_grid_view";
import { TimerTimesheetGridController } from "./timer_timesheet_grid_controller";
import { TimerTimesheetGridModel } from "./timer_timesheet_grid_model";
import { TimerTimesheetGridRenderer } from "./timer_timesheet_grid_renderer";

export const timerTimesheetGridView = {
    ...timesheetGridView,
    Controller: TimerTimesheetGridController,
    Model: TimerTimesheetGridModel,
    Renderer: TimerTimesheetGridRenderer,
};

registry.category("views").add("timer_timesheet_grid", timerTimesheetGridView);
