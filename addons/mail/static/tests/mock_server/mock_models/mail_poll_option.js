import { fields, models } from "@web/../tests/web_test_helpers";

export class MailPollOption extends models.ServerModel {
    _name = "mail.poll.option";

    option_label = fields.Char();
    poll_id = fields.Many2one({ relation: "mail.poll" });

    _store_poll_option_fields(res) {
        res.extend([
            "number_of_votes",
            "poll_id",
            "option_emoji",
            "option_label",
            "vote_percentage",
        ]);
        if (res.is_for_current_user()) {
            res.attr("selected_by_self");
        }
    }
}
