/** @odoo-module */

import { ListRenderer } from "@web/views/list/list_renderer";
import { TimesheetTimerHeader } from "@timesheet_grid/components/timesheet_timer_header/timesheet_timer_header";
import { useTimesheetTimerRendererHook } from "@timesheet_grid/hooks/timesheet_timer_hooks";

export class TimesheetTimerListRenderer extends ListRenderer {
    static template = "timesheet_grid.TimesheetTimerListRenderer";
    static components = {
        ...ListRenderer.components,
        TimesheetTimerHeader: TimesheetTimerHeader,
    };
    static props = [...ListRenderer.props, "timerState"];

    setup() {
        super.setup();
        this.timesheetTimerRendererHook = useTimesheetTimerRendererHook();
    }

    onGlobalClick(ev) {
        if (ev.target.closest(".timesheet-timer")) {
            return;
        }
        super.onGlobalClick(ev);
    }
}
