/* @odoo-module */

import { useMessaging } from "@mail/core/messaging_hook";
import { useTypingService } from "@mail/discuss/typing/typing_service";
import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { sprintf } from "@web/core/utils/strings";

/**
 * @typedef {Object} Props
 * @property {import("@mail/core/thread_model").Thread} channel
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
    static template = "discuss.Typing";

    setup() {
        this.messaging = useMessaging();
        this.typingService = useTypingService();
    }

    /** @returns {string} */
    get text() {
        const typingMemberNames = this.typingService
            .getTypingMembers(this.props.channel)
            .map(({ persona }) => this.props.channel.getMemberName(persona));
        if (typingMemberNames.length === 1) {
            return sprintf(_t("%s is typing..."), typingMemberNames[0]);
        }
        if (typingMemberNames.length === 2) {
            return sprintf(
                _t("%s and %s are typing..."),
                typingMemberNames[0],
                typingMemberNames[1]
            );
        }
        return sprintf(
            _t("%s, %s and more are typing..."),
            typingMemberNames[0],
            typingMemberNames[1]
        );
    }
}
