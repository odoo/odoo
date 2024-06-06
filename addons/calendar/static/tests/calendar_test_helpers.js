import { CalendarEvent } from "./mock_server/mock_models/calendar_event";
import { CalendarAttendee } from "./mock_server/mock_models/calendar_attendee";
import { ResUsers } from "./mock_server/mock_models/res_users";
import { MailActivity } from "./mock_server/mock_models/mail_activity";

import { mailModels } from "@mail/../tests/mail_test_helpers";
import { busModels } from "@bus/../tests/bus_test_helpers";
import { defineModels, webModels } from "@web/../tests/web_test_helpers";

export const calendarModels = {
    CalendarAttendee,
    CalendarEvent,
    ResUsers,
    MailActivity,
};

export function defineCalendarModels() {
    return defineModels({ ...webModels, ...busModels, ...mailModels, ...calendarModels });
}
