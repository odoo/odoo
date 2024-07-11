/* @odoo-module */

import { Component, useState } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

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

    setup() {
        this.typingService = useState(useService("discuss.typing"));
    }

    /** @returns {string} */
    get text() {
        const typingMemberNames = this.typingService
            .getTypingMembers(this.props.channel)
            .map(({ persona }) => this.props.channel.getMemberName(persona));
        if (typingMemberNames.length === 1) {
            return _t("%s is typing...", typingMemberNames[0]);
        }
        if (typingMemberNames.length === 2) {
            return _t("%s and %s are typing...", typingMemberNames[0], typingMemberNames[1]);
        }
        return _t("%s, %s and more are typing...", typingMemberNames[0], typingMemberNames[1]);
    }
}
