import { CalendarEvent } from "./mock_server/mock_models/calendar_event";
import { CalendarAttendee } from "./mock_server/mock_models/calendar_attendee";
import { CalendarFilters } from "./mock_server/mock_models/calendar_filters";
import { MailActivity } from "./mock_server/mock_models/mail_activity";
import { ResPartner } from "./mock_server/mock_models/res_partner";
import { ResUsers } from "./mock_server/mock_models/res_users";

import { mailModels } from "@mail/../tests/mail_test_helpers";
import { defineModels } from "@web/../tests/web_test_helpers";

export const calendarModels = {
    CalendarAttendee,
    CalendarEvent,
    CalendarFilters,
    MailActivity,
    ResPartner,
    ResUsers,
};

export function defineCalendarModels() {
    return defineModels({ ...mailModels, ...calendarModels });
}
