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
    vote_ids = fields.Many("mail.poll.vote", { inverse: "option_id" });
    /** @type {number} */
    vote_percentage;

    async fetchPollVotesCached() {
        if (!this.votesFetched) {
            try {
                this.votesFetched = true;
                await this.store.fetchStoreData("/mail/poll_option/votes", {
                    poll_option_id: this.id,
                });
            } catch (e) {
                this.votesFetched = false;
                throw e;
            }
        }
    }
}
MailPollOptionModel.register();
