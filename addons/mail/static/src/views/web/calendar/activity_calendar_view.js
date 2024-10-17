import { registry } from "@web/core/registry";
import { calendarView } from "@web/views/calendar/calendar_view";
import { ActivityCalendarRender } from "./activity_calendar_renderer";

const activityCalendarView = {
    ...calendarView,
    Renderer: ActivityCalendarRender,
};

registry.category("views").add("activity_calendar", activityCalendarView);
