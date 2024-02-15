import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * @typedef {Object} Props
 * @property {import("models").Message} message
 * @property {import("models").Thread} thread
 * @extends {Component<Props, Env>}
 */
export class MessageSeenIndicator extends Component {
    static template = "mail.MessageSeenIndicator";
    static props = ["message", "thread", "className?"];

    setup() {
        this.store = useState(useService("mail.store"));
    }

    get hasEveryoneSeen() {
        const otherDidNotSee = this.props.thread.channelMembers.filter((member) => {
            return (
                member.persona.notEq(this.props.message.author) &&
                (!member.seen_message_id || member.seen_message_id.id < this.props.message.id)
            );
        });
        return otherDidNotSee.length === 0;
    }

    get hasEveryoneReceived() {
        return !this.props.thread.channelMembers.some((member) => {
            return (
                member.persona.notEq(this.props.message.author) &&
                (!member.fetched_message_id || member.fetched_message_id.id < this.props.message.id)
            );
        });
    }

    get isMessagePreviousToLastSelfMessageSeenByEveryone() {
        if (!this.props.thread.lastSelfMessageSeenByEveryone) {
            return false;
        }
        return this.props.message.id < this.props.thread.lastSelfMessageSeenByEveryone.id;
    }

    get hasSomeoneSeen() {
        const otherSeen = this.props.thread.channelMembers.filter(
            (member) =>
                member.persona.notEq(this.props.message.author) &&
                member.seen_message_id?.id >= this.props.message.id
        );
        return otherSeen.length > 0;
    }

    get hasSomeoneFetched() {
        const otherFetched = this.props.thread.channelMembers.filter(
            (member) =>
                member.persona.notEq(this.props.message.author) &&
                member.fetched_message_id?.id >= this.props.message.id
        );
        return otherFetched.length > 0;
    }
}
