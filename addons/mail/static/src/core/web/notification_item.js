/* @odoo-module */

import { ImStatus } from "@mail/core/common/im_status";
import { RelativeTime } from "@mail/core/common/relative_time";
import { useHover } from "@mail/utils/common/hooks";

import { Component, useRef } from "@odoo/owl";

import { ActionSwiper } from "@web/core/action_swiper/action_swiper";

export class NotificationItem extends Component {
    static components = { ActionSwiper, RelativeTime, ImStatus };
    static props = [
        "body?",
        "counter?",
        "datetime?",
        "displayName?",
        "hasMarkAsReadButton?",
        "iconSrc?",
        "muted?",
        "onClick",
        "onSwipeLeft?",
        "onSwipeRight?",
        "slots?",
    ];
    static defaultProps = {
        counter: 0,
        displayName: "",
        muted: 0,
    };
    static template = "mail.NotificationItem";

    setup() {
        this.markAsReadRef = useRef("markAsRead");
        this.rootHover = useHover("root");
    }

    onClick(ev) {
        this.props.onClick(ev.target === this.markAsReadRef.el);
    }
}
