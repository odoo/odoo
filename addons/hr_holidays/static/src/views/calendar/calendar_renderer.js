import { useService } from "@web/core/utils/hooks";
import { CalendarRenderer } from "@web/views/calendar/calendar_renderer";
import { TimeOffDashboard } from "../../dashboard/time_off_dashboard";
import { TimeOffCalendarCommonRenderer } from "./common/calendar_common_renderer";
import { TimeOffCalendarYearRenderer } from "./year/calendar_year_renderer";

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
    setup() {
        super.setup();
        this.uiService = useService("ui");
    }
    get showDashboard() {
        return !this.uiService.isSmall;
    }
}
