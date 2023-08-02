/* @odoo-module */

import { useStore } from "@mail/core/common/messaging_hook";
import { createObjectId } from "@mail/utils/common/misc";

import { Component } from "@odoo/owl";

/**
 * @typedef {Object} Props
 * @property {import("@mail/core/common/thread_model").Thread} thread
 * @property {string} size
 * @property {string} className
 * @extends {Component<Props, Env>}
 */
export class ThreadIcon extends Component {
    static template = "mail.ThreadIcon";
    static props = ["thread", "size?", "className?"];
    static defaultProps = {
        size: "medium",
        className: "",
    };

    setup() {
        this.store = useStore();
    }

    get chatPartner() {
        return this.store.Persona.records[
            createObjectId("Persona", "partner", this.props.thread.chatPartnerId)
        ];
    }
}
