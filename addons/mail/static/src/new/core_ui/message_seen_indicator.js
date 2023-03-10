/* @odoo-module */

import { Component } from "@odoo/owl";
import { useStore } from "../core/messaging_hook";

/**
 * @typedef {Object} Props
 * @property {import("@mail/new/core/message_model").Message} message
 * @property {import("@mail/new/core/thread_model").Thread} thread
 * @extends {Component<Props, Env>}
 */
export class MessageSeenIndicator extends Component {
    static template = "mail.MessageSeenIndicator";
    static props = ["message", "thread", "className?"];

    setup() {
        this.store = useStore();
    }

    get hasEveryoneSeen() {
        const otherDidNotSee = [...this.props.thread.seenInfos].filter((seenInfo) => {
            return (
                seenInfo.partner.id !== this.props.message.author.id &&
                (!seenInfo.lastSeenMessage || seenInfo.lastSeenMessage.id < this.props.message.id)
            );
        });
        return otherDidNotSee.length === 0;
    }

    get isMessagePreviousToLastSelfMessageSeenByEveryone() {
        if (!this.props.thread.lastSelfMessageSeenByEveryone) {
            return false;
        }
        return this.props.message.id < this.props.thread.lastSelfMessageSeenByEveryone.id;
    }

    get hasSomeoneSeen() {
        const otherSeen = [...this.props.thread.seenInfos].filter(
            (seenInfo) =>
                seenInfo.partner.id !== this.props.message.author.id &&
                seenInfo.lastSeenMessage?.id >= this.props.message.id
        );
        return otherSeen.length > 0;
    }

    get hasSomeoneFetched() {
        const otherFetched = [...this.props.thread.seenInfos].filter(
            (seenInfo) =>
                seenInfo.partner.id !== this.props.message.author.id &&
                seenInfo.lastFetchedMessage?.id >= this.props.message.id
        );
        return otherFetched.length > 0;
    }
}
