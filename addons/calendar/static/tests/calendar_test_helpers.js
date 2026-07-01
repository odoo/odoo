import { CalendarAttendee } from "./mock_server/mock_models/calendar_attendee";
import { CalendarCalendar } from "./mock_server/mock_models/calendar_calendar";
import { CalendarCalendarUser } from "./mock_server/mock_models/calendar_calendar_user";
import { CalendarEvent } from "./mock_server/mock_models/calendar_event";
import { CalendarFilters } from "./mock_server/mock_models/calendar_filters";
import { ResUsers } from "./mock_server/mock_models/res_users";
import { MailActivity } from "./mock_server/mock_models/mail_activity";

import { mailModels } from "@mail/../tests/mail_test_helpers";
import { defineModels } from "@web/../tests/web_test_helpers";

export const calendarModels = {
    CalendarAttendee,
    CalendarCalendar,
    CalendarCalendarUser,
    CalendarEvent,
    CalendarFilters,
    ResUsers,
    MailActivity,
};

export function defineCalendarModels() {
    return defineModels({ ...mailModels, ...calendarModels });
}
