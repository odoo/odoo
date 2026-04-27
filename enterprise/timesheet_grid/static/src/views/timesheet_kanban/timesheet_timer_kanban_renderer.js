/** @odoo-module */

import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { TimesheetTimerHeader } from "@timesheet_grid/components/timesheet_timer_header/timesheet_timer_header";
import { useTimesheetTimerRendererHook } from "@timesheet_grid/hooks/timesheet_timer_hooks";

export class TimesheetTimerKanbanRenderer extends KanbanRenderer {
    static template = "timesheet_grid.TimesheetTimerKanbanRenderer";
    static components = {
        ...KanbanRenderer.components,
        TimesheetTimerHeader: TimesheetTimerHeader,
    };
    setup() {
        super.setup();
        this.timesheetTimerRendererHook = useTimesheetTimerRendererHook();
    }
}
