import { fields, models } from "@web/../tests/web_test_helpers";

export class MailPollOption extends models.ServerModel {
    _name = "mail.poll.option";

    option_label = fields.Char();
    poll_id = fields.Many2one({ relation: "mail.poll" });

    _store_poll_option_fields(res) {
        res.extend(["option_label", "poll_id"]);
    }
}
