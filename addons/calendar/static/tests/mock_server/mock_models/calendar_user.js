import { fields, models, serverState } from "@web/../tests/web_test_helpers";

export class CalendarUser extends models.ServerModel {
    _name = "calendar.user";

    user_id = fields.Many2one({ default: serverState.userId });
}
