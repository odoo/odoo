import { fields } from "@mail/model/misc";
import { Record } from "@mail/model/record";

export class MailPollOptionModel extends Record {
    static id = "id";
    static _name = "mail.poll.option";

    /** @type {number} */
    id;
    /** @type {number} */
    number_of_vote;
    /** @type {string} */
    option_label;
    poll_id = fields.One("mail.poll");
    /** @type {boolean} */
    selected_by_self;
    /** @type {number} */
    vote_percentage;
}
MailPollOptionModel.register();
