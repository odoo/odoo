import { fields } from "@mail/model/misc";
import { Record } from "@mail/model/record";

export class MailPollOptionModel extends Record {
    static _name = "mail.poll.option";

    static new() {
        const option = super.new(...arguments);
        option.fetchPollVotesCached = option.store.makeCachedFetchData("/mail/poll_option/votes", {
            poll_option_id: option.id,
        });
        return option;
    }

    /** @type {ReturnType<import("models").Store['makeCachedFetchData']>} */
    fetchPollVotesCached;
    /** @type {number} */
    id;
    /** @type {number} */
    number_of_vote;
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
