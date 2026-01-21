import { fields } from "@mail/model/misc";
import { Record } from "@mail/model/record";

export class MailPollVote extends Record {
    static _name = "mail.poll.vote";
    static id = "id";

    /** @type {number} */
    id;
    guest_id = fields.One("mail.guest");
    option_id = fields.One("mail.poll.option", { inverse: "vote_ids" });
    user_id = fields.One("res.users");
}
MailPollVote.register();
