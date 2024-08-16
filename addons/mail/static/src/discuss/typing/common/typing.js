import { Component } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";

/**
 * @typedef {Object} Props
 * @property {import("models").Thread} channel
 * @property {string} [size]
 * @property {boolean} [displayText]
 * @extends {Component<Props, Env>}
 */
export class Typing extends Component {
    static defaultProps = {
        size: "small",
        displayText: true,
    };
    static props = ["channel?", "size?", "displayText?", "member?"];
    static template = "discuss.Typing";

    /** @returns {string} */
    get text() {
        const typingMemberNames = this.props.member
            ? [this.props.member.name]
            : this.props.channel.otherTypingMembers.map(({ name }) => name);
        if (typingMemberNames.length === 1) {
            return _t("%s is typing...", typingMemberNames[0]);
        }
        if (typingMemberNames.length === 2) {
            return _t("%(user1)s and %(user2)s are typing...", {
                user1: typingMemberNames[0],
                user2: typingMemberNames[1],
            });
        }
        return _t("%(user1)s, %(user2)s and more are typing...", {
            user1: typingMemberNames[0],
            user2: typingMemberNames[1],
        });
    }
}
