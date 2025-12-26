import { WorkEntryDashboard } from "@hr_work_entry/dashboard/work_entry_dashboard";
import { WorkEntryCalendarCommonRenderer } from "@hr_work_entry/views/work_entry_calendar/calendar_common/work_entry_calendar_common_renderer";
import { CalendarRenderer } from "@web/views/calendar/calendar_renderer";

export class WorkEntryCalendarRenderer extends CalendarRenderer {
    static template = "hr_work_entry.CalendarRenderer";
    static components = {
        ...CalendarRenderer.components,
        month: WorkEntryCalendarCommonRenderer,
        WorkEntryDashboard,
    };

    get employeeId() {
        return this.props.model.meta?.context?.default_employee_id;
    }

    get rangeStart() {
        // Use the calendar's focused date, not the grid range start.
        // In month view, range.start often includes leading days from the previous month.
        return this.props.model.date;
    }

    get rangeEnd() {
        return this.props.model.data?.range?.end;
    }

    get dashboardReloadKey() {
        return this.props.model.data?.dashboardReloadKey;
    }

    get showDashboard() {
        return !this.env.isSmall && Boolean(this.employeeId) && Boolean(this.rangeStart);
    }
}
