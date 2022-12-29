/* @odoo-module */

import { Component, useRef } from "@odoo/owl";
import { PartnerImStatus } from "@mail/new/discuss/partner_im_status";
import { RelativeTime } from "../core_ui/relative_time";

export class NotificationItem extends Component {
    static components = { RelativeTime, PartnerImStatus };
    static props = [
        "body?",
        "count?",
        "dateTime?",
        "displayName",
        "hasMarkAsReadButton?",
        "iconSrc",
        "isLast",
        "onClick",
        "slots?",
    ];
    static template = "mail.notification_item";

    setup() {
        this.markAsReadRef = useRef("markAsRead");
    }

    onClick(ev) {
        this.props.onClick(ev.target === this.markAsReadRef.el);
    }
}
