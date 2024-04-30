import { models } from "@web/../tests/web_test_helpers";

export class CalendarEvent extends models.ServerModel {
    _name = "calendar.event";

    check_access_rights() {
        return true;
    }
}
