import { fields, models } from "@web/../tests/web_test_helpers";

export class MailPoll extends models.ServerModel {
    _name = "mail.poll";

    end_message_id = fields.Many2one({ relation: "mail.message" });
    poll_end_dt = fields.Datetime();
    poll_question = fields.Char();
    option_ids = fields.One2many({ relation: "mail.poll.option", relation_field: "poll_id" });
    start_message_id = fields.Many2one({ relation: "mail.message" });
    winning_option_id = fields.Many2one({ relation: "mail.poll.option" });

    _store_poll_fields(res) {
        res.extend(["end_message_id", "poll_question", "start_message_id", "winning_option_id"]);
        res.many("option_ids", "_store_poll_option_fields");
    }
}
