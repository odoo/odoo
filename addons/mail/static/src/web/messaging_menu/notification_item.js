/* @odoo-module */

import { Component, useRef } from "@odoo/owl";
import { ImStatus } from "@mail/discuss_app/im_status";
import { RelativeTime } from "@mail/core_ui/relative_time";
import { ActionSwiper } from "@web/core/action_swiper/action_swiper";

export class NotificationItem extends Component {
    static components = { ActionSwiper, RelativeTime, ImStatus };
    static props = [
        "body?",
        "counter?",
        "datetime?",
        "displayName",
        "hasMarkAsReadButton?",
        "iconSrc?",
        "isLast",
        "onClick",
        "onSwipeLeft?",
        "onSwipeRight?",
        "slots?",
    ];
    static defaultProps = {
        counter: 0,
    };
    static template = "mail.NotificationItem";

    setup() {
        this.markAsReadRef = useRef("markAsRead");
    }

    onClick(ev) {
        this.props.onClick(ev.target === this.markAsReadRef.el);
    }
}
