/** @odoo-module native */
import { CalendarRenderer } from "@web/views/calendar";

import { TimeOffDashboard } from "../../dashboard/time_off_dashboard.js";
import { TimeOffCalendarCommonRenderer } from "./common/calendar_common_renderer.js";
import { TimeOffCalendarYearRenderer } from "./year/calendar_year_renderer.js";

export class TimeOffCalendarRenderer extends CalendarRenderer {
    static template = "hr_holidays.CalendarRenderer";
    static components = {
        ...TimeOffCalendarRenderer.components,
        day: TimeOffCalendarCommonRenderer,
        week: TimeOffCalendarCommonRenderer,
        month: TimeOffCalendarCommonRenderer,
        year: TimeOffCalendarYearRenderer,
        TimeOffDashboard,
    };
    get employeeId() {
        return this.props.model.employeeId;
    }

    get showDashboard() {
        return false;
    }
}

export class TimeOffDashboardCalendarRenderer extends TimeOffCalendarRenderer {
    get showDashboard() {
        // The same calendar view serves the employee's own time off and the
        // officer's "All Time Off". Only the first is about the reader, so only
        // the first should carry their personal balance.
        const isManagementRelated =
            this.props?.model?.meta?.context?.is_management_related ?? false;
        return !this.env.isSmall && !isManagementRelated;
    }
}
