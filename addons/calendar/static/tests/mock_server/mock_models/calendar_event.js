import { mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";
import { models, fields, serverState } from "@web/../tests/web_test_helpers";

export class CalendarEvent extends models.ServerModel {
    _name = "calendar.event";

    start = fields.Datetime();
    stop = fields.Datetime();
    user_id = fields.Generic({ default: serverState.userId });
    partner_id = fields.Generic({ default: serverState.partnerId });
    partner_ids = fields.Generic({ default: [[6, 0, [serverState.partnerId]]] });

    has_access() {
        return true;
    }

    get_default_duration() {
        return 3.25;
    }

    _store_calendar_event_fields() {
        return ["start", "stop", mailDataHelpers.Store.many("partner_ids", ["name"])];
    }
}
