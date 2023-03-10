/* @odoo-module */

import { Component } from "@odoo/owl";
import { useStore } from "@mail/new/core/messaging_hook";
import { Typing } from "@mail/new/composer/typing";
import { createLocalId } from "@mail/new/utils/misc";

/**
 * @typedef {Object} Props
 * @property {import("@mail/new/core/thread_model").Thread} thread
 * @property {string} size
 * @property {string} className
 * @extends {Component<Props, Env>}
 */
export class ThreadIcon extends Component {
    static template = "mail.ThreadIcon";
    static components = { Typing };
    static props = ["thread", "size?", "className?"];
    static defaultProps = {
        size: "medium",
        className: "",
    };

    setup() {
        this.store = useStore();
    }

    get chatPartner() {
        return this.store.personas[createLocalId("partner", this.props.thread.chatPartnerId)];
    }
}
