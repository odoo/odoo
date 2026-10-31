import { models } from "@web/../tests/web_test_helpers";

export class MailPollOption extends models.ServerModel {
    _name = "mail.poll.option";

    _store_poll_option_fields(res) {
        res.extend(["number_of_votes", "poll_id", "option_label", "vote_percentage"]);
        if (res.is_for_current_user()) {
            res.attr("selected_by_self");
        }
    }
}
