import { Component, useRef } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
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
        super.setup();
        this.root = useRef("root");
        this.dialog = useService("dialog");
    }

    openModal() {
        this.dialog.add(MessageSeenIndicatorDialog, { message: this.props.message });
    }
}

class MessageSeenIndicatorDialog extends Component {
    static components = { Dialog };
    static template = "mail.MessageSeenIndicator.dialog";
    static props = ["message", "close?"];
}
