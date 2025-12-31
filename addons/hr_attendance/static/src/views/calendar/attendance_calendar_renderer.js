import { serializeDateTime } from "@web/core/l10n/dates";
import { CalendarRenderer } from "@web/views/calendar/calendar_renderer";
import { AttendanceCalendarOverview } from "../../components/attendance_calendar/attendance_calendar_overview";

export class AttendanceCalendarRenderer extends CalendarRenderer {
    static template = "hr_attendance.AttendanceCalendarRenderer";
    static components = {
        ...CalendarRenderer.components,
        AttendanceCalendarOverview,
    };

    get dateRange() {
        /* Returns the start and end date corresponding to the current view's date range.
        We cannot use model.data.range because in month view the visible calendar may
        include overflow days from the previous or next month*/
        const { scale, date, firstDayOfWeek } = this.props.model.meta;
        let start; let end;
        if (scale === "week") {
            const offset = (date.weekday - firstDayOfWeek + 7) % 7;
            start = date.minus({ days: offset }).startOf("day");
            end = start.plus({ days: 6 }).endOf("day");
        } else {
            start = date.startOf(scale).startOf("day");
            end = date.endOf(scale).endOf("day");
        }
        return {
            start: serializeDateTime(start),
            end: serializeDateTime(end),
        };
    }
}
