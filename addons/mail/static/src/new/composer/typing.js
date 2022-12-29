/* @odoo-module */

import { Component } from "@odoo/owl";
import { sprintf } from "@web/core/utils/strings";
import { useMessaging } from "../core/messaging_hook";

import { _t } from "@web/core/l10n/translation";

/**
 * @typedef {Object} Props
 * @property {number} channel_id
 * @property {string} size
 * @property {boolean} displayText
 * @extends {Component<Props, Env>}
 */
export class Typing extends Component {
    static defaultProps = {
        size: "small",
        displayText: true,
    };
    static props = ["channel", "size?", "displayText?"];
    static template = "mail.typing";

    setup() {
        this.messaging = useMessaging();
    }

    /** @returns {boolean|string} */
    get text() {
        if (this.props.channel.hasTypingMembers) {
            const typingMembers = this.props.channel.typingMembers;
            if (typingMembers.length === 1) {
                return sprintf(_t("%s is typing..."), typingMembers[0].persona.name);
            }
            if (typingMembers.length === 2) {
                return sprintf(
                    _t("%s and %s are typing..."),
                    typingMembers[0].persona.name,
                    typingMembers[1].persona.name
                );
            }
            return sprintf(
                _t("%s, %s and more are typing..."),
                typingMembers[0].persona.name,
                typingMembers[1].persona.name
            );
        }
        return false;
    }
}
