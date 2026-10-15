import { calendarView } from "@web/views/calendar/calendar_view";

import { TimeOffCalendarController } from "./calendar_controller";
import { TimeOffCalendarModel } from "./calendar_model";
import { TimeOffCalendarRenderer, TimeOffDashboardCalendarRenderer } from "./calendar_renderer";

import { registry } from "@web/core/registry";
import { HrHolidaysSearchModel } from "@hr_holidays/search/hr_holidays_search_model";

export const timeOffCalendarHrLeaveView = {
    ...calendarView,
    Controller: TimeOffCalendarController,
    Renderer: TimeOffCalendarRenderer,
    Model: TimeOffCalendarModel,
    SearchModel: HrHolidaysSearchModel,
    buttonTemplate: "hr_holidays.CalendarController.Buttons",
};

registry.category("views").add("time_off_calendar_dashboard", {
    ...timeOffCalendarHrLeaveView,
    Renderer: TimeOffDashboardCalendarRenderer,
});
