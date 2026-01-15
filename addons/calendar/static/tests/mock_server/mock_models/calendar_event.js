import { models, fields, serverState } from "@web/../tests/web_test_helpers";

export class CalendarEvent extends models.ServerModel {
    _name = "calendar.event";

    user_id = fields.Generic({ default: serverState.userId });
    partner_id = fields.Generic({ default: serverState.partnerId });
    partner_ids = fields.Generic({ default: [[6, 0, [serverState.partnerId]]] });

    has_access() {
        return true;
    }

    get_default_duration() {
        return 3.25;
    }
}
