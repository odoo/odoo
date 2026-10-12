import { fields } from "@mail/model/misc";
import { Record } from "@mail/model/record";

export class MailPollOptionModel extends Record {
    static _name = "mail.poll.option";

    fetchPollVotesCached = this.computed(() =>
        this.store.makeCachedFetchData("/mail/poll_option/votes", { poll_option_id: this.id })
    );
    /** @type {number} */
    id;
    /** @type {number} */
    number_of_votes;
    /** @type {string} */
    option_emoji;
    /** @type {string} */
    option_label;
    poll_id = fields.One("mail.poll");
    /** @type {boolean} */
    selected_by_self;
    vote_ids = fields.Many("mail.poll.vote", { inverse: "option_id" });
    /** @type {number} */
    vote_percentage;
}
MailPollOptionModel.register();
