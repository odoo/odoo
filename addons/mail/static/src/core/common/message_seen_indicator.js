import { Component, useRef } from "@odoo/owl";
import { usePopover } from "@web/core/popover/popover_hook";
import { MessageSeenIndicatorPopover } from "./message_seen_indicator_popover";

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
        this.popover = usePopover(MessageSeenIndicatorPopover);
        this.root = useRef("root");
    }

    onClick() {
        if (!this.popover.isOpen && this.props.message.channelMemberHaveSeen.length > 0) {
            this.popover.open(this.root.el, { message: this.props.message });
        }
    }
}
