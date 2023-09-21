/* @odoo-module */

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
        const otherDidNotSee = [...this.props.thread.seenInfos].filter((seenInfo) => {
            return (
                seenInfo.partner.id !== this.props.message.author?.id &&
                (!seenInfo.lastSeenMessage || seenInfo.lastSeenMessage.id < this.props.message.id)
            );
        });
        return otherDidNotSee.length === 0;
    }

    get hasEveryoneReceived() {
        return ![...this.props.thread.seenInfos].some((seenInfo) => {
            return (
                seenInfo.partner.id !== this.props.message.author.id &&
                (!seenInfo.lastFetchedMessage ||
                    seenInfo.lastFetchedMessage.id < this.props.message.id)
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
        const otherSeen = [...this.props.thread.seenInfos].filter(
            (seenInfo) =>
                seenInfo.partner.id !== this.props.message.author?.id &&
                seenInfo.lastSeenMessage?.id >= this.props.message.id
        );
        return otherSeen.length > 0;
    }

    get hasSomeoneFetched() {
        const otherFetched = [...this.props.thread.seenInfos].filter(
            (seenInfo) =>
                seenInfo.partner.id !== this.props.message.author?.id &&
                seenInfo.lastFetchedMessage?.id >= this.props.message.id
        );
        return otherFetched.length > 0;
    }
}
