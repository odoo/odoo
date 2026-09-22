import { models, fields, serverState } from "@web/../tests/web_test_helpers";

export class CalendarEvent extends models.ServerModel {
    _name = "calendar.event";

    user_id = fields.Many2one({ default: serverState.userId });
    partner_id = fields.Many2one({ default: serverState.partnerId });
    partner_ids = fields.Many2many({ default: [[6, 0, [serverState.partnerId]]] });

    has_access() {
        return true;
    }

    get_default_duration() {
        return 3.25;
    }
}
