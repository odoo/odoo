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
    static props = ["channel", "size?", "displayText?"];
    static template = "discuss.Typing";

    /** @returns {string} */
    get text() {
        const typingMemberNames = this.props.channel.otherTypingMembers.map(({ persona }) =>
            this.props.channel.getMemberName(persona)
        );
        if (typingMemberNames.length === 1) {
            return _t("%s is typing...", typingMemberNames[0]);
        }
        if (typingMemberNames.length === 2) {
            return _t("%s and %s are typing...", typingMemberNames[0], typingMemberNames[1]);
        }
        return _t("%s, %s and more are typing...", typingMemberNames[0], typingMemberNames[1]);
    }
}
