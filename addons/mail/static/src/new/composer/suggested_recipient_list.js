/* @odoo-module */

import { Component, useState } from "@odoo/owl";
import { SuggestedRecipient } from "@mail/new/composer/suggested_recipient";

/**
 * @typedef {Object} Props
 * @property {import("@mail/new/core/thread_model").Thread} thread
 * @property {string} className
 * @property {string} styleString
 * @extends {Component<Props, Env>}
 */
export class SuggestedRecipientsList extends Component {
    static template = "mail.suggested_recipients_list";
    static components = { SuggestedRecipient };
    static props = ["thread", "className", "styleString"];

    setup() {
        this.state = useState({
            showMore: false,
        });
    }

    get suggestedRecipients() {
        if (!this.state.showMore) {
            return this.props.thread.suggestedRecipients.slice(0, 3);
        }
        return this.props.thread.suggestedRecipients;
    }
}
