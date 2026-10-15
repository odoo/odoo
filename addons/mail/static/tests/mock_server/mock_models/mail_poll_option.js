import { models } from "@web/../tests/web_test_helpers";

export class MailPollOption extends models.ServerModel {
    _name = "mail.poll.option";

    get _to_store_defaults() {
        return [
            "number_of_votes",
            "poll_id",
            "option_label",
            "vote_percentage",
            "selected_by_self",
        ];
    }
}
