import { fields, models } from "@web/../tests/web_test_helpers";

export class MailPoll extends models.ServerModel {
    _name = "mail.poll";

    end_message_id = fields.Many2one({ relation: "mail.message" });
    option_ids = fields.One2many({ relation: "mail.poll.option", relation_field: "poll_id" });
    poll_end_dt = fields.Datetime();
    poll_question = fields.Char();
    start_message_id = fields.Many2one({ relation: "mail.message" });
    winning_option_id = fields.Many2one({ relation: "mail.poll.option" });

    _store_poll_fields(res, { with_start_message_id = true } = {}) {
        res.extend(["allow_multiple_options", "create_date", "create_uid", "end_message_id"]);
        res.many("option_ids", "_store_poll_option_fields");
        res.extend(["poll_end_dt", "poll_question", "winning_option_id"]);
        if (with_start_message_id) {
            res.one("start_message_id", "_store_message_fields");
        }
    }
}
