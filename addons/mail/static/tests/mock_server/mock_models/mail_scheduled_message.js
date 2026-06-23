import { fields, models, serverState } from "@web/../tests/web_test_helpers";

export class MailScheduledMessage extends models.ServerModel {
    _inherit = "mail.scheduled.message";

    author_id = fields.Generic({ default: () => serverState.partnerId });

    _store_scheduled_message_fields(res) {
        res.many("attachment_ids", "_store_attachment_fields");
        res.one("author_id", "_store_partner_fields");
        res.attr("body", (m) => ["markup", m.body]);
        res.extend(["is_note", "scheduled_date", "subject"]);
    }
}
