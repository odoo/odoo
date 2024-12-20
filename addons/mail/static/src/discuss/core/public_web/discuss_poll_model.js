import { Record } from "@mail/model/record";
import { rpc } from "@web/core/network/rpc";

export class DiscussPollModel extends Record {
    static id = "id";
    static _name = "discuss.poll";

    /** @type {number} */
    id;
    /** @type {string} */
    answer_ids = Record.many("discuss.poll.answer");
    closed = false;
    create_date = Record.attr(undefined, { type: "datetime" });
    /** @type {number} */
    duration;
    end_message_id = Record.one("mail.message");
    start_message_id = Record.one("mail.message");
    /** @type {number} */
    number_of_votes;
    question;
    winning_answer_id = Record.one("discuss.poll.answer");

    vote(answerIds) {
        rpc("/discuss/poll/vote", { poll_id: this.id, answer_ids: answerIds });
    }

    removeVote() {
        rpc("/discuss/poll/remove_vote", { poll_id: this.id });
    }

    get selfAlreadyVoted() {
        return this.answer_ids.some((answer) => answer.selectedBySelf);
    }

    get remainingTime() {
        return this.create_date.plus({ hours: this.duration }).diffNow().toFormat("hh'h'mm");
    }
}
DiscussPollModel.register();
