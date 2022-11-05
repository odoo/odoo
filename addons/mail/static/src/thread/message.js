/** @odoo-module */

import { useMessaging } from "../messaging_hook";
import { RelativeTime } from "./relative_time";
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class Message extends Component {
    static template = "mail.message";
    static components = { RelativeTime };
    static props = ["message", "squashed?"];

    setup() {
        this.messaging = useMessaging();
        this.action = useService("action");
        this.message = this.props.message;
        this.author = this.messaging.partners[this.message.authorId];
    }

    toggleStar() {
        this.messaging.toggleStar(this.props.message.id);
    }

    openRecord() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_id: this.message.resId,
            res_model: this.message.resModel,
            views: [[false, "form"]],
        });
    }
}
