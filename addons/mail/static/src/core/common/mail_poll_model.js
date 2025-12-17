import { fields } from "@mail/model/misc";
import { Record } from "@mail/model/record";

import { markup } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";

export class MailPollModel extends Record {
    static id = "id";
    static _name = "mail.poll";

    /** @type {boolean|undefined} */
    allow_multiple_options;
    create_date = fields.Datetime();
    create_uid = fields.One("res.users");
    /** @type {number} */
    id;
    end_message_id = fields.One("mail.message");
    option_ids = fields.Many("mail.poll.option");
    poll_end_dt = fields.Datetime();
    /** @type {string|undefined} */
    poll_question;
    start_message_id = fields.One("mail.message");
    winning_option_id = fields.One("mail.poll.option");

    get createdBySelf() {
        return this.store.self_user?.eq(this.create_uid);
    }

    get numberOfVotes() {
        return this.option_ids.reduce((sum, option) => sum + option.number_of_votes, 0);
    }

    get pollClosedText() {
        return _t(
            '%(author)s\'s poll %(strong_tag_start)s"%(question)s"%(strong_tag_end)s has closed.',
            {
                author: this.start_message_id.authorName,
                question: this.poll_question,
                strong_tag_start: markup`<strong>`,
                strong_tag_end: markup`</strong>`,
            }
        );
    }

    get selfAlreadyVoted() {
        return this.option_ids.some((option) => option.selected_by_self);
    }

    removeVote() {
        rpc("/mail/poll/remove_vote", { poll_id: this.id });
    }

    async vote(optionIds) {
        await rpc("/mail/poll/vote", { poll_id: this.id, option_ids: optionIds });
    }
}
MailPollModel.register();
