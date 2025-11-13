import { CalendarMobileFilterPanel } from "@web/views/calendar/mobile_filter_panel/calendar_mobile_filter_panel";

export class TimeOffCalendarMobileFilterPanel extends CalendarMobileFilterPanel {
    static components = {
        ...CalendarMobileFilterPanel.components,
    };
    static template = "hr_holidays.TimeOffCalendarMobileFilterPanel";

}
