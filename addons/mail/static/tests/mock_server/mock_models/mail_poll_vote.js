import { models } from "@web/../tests/web_test_helpers";

export class MailPollVote extends models.ServerModel {
    _name = "mail.poll.vote";

    _store_vote_fields(res) {
        res.one("option_id", []);
        res.one("user_id", (r) =>
            r.one("partner_id", (r) => {
                r.from_method("_store_avatar_fields");
                r.attr("name");
            })
        );
        res.one("guest_id", (r) => {
            r.from_method("_store_avatar_fields");
            r.attr("name");
        });
    }
}
