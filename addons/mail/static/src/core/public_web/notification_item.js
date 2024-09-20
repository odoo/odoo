import { ImStatus } from "@mail/core/common/im_status";
import { isToday } from "@mail/utils/common/dates";
import { useHover } from "@mail/utils/common/hooks";

import { Component, useRef, useState } from "@odoo/owl";

import { ActionSwiper } from "@web/core/action_swiper/action_swiper";
import { useService } from "@web/core/utils/hooks";

const { DateTime } = luxon;

export class NotificationItem extends Component {
    static components = { ActionSwiper, ImStatus };
    static props = [
        "body?",
        "counter?",
        "datetime?",
        "first?",
        "hasMarkAsReadButton?",
        "iconSrc?",
        "muted?",
        "onClick",
        "onSwipeLeft?",
        "onSwipeRight?",
        "slots?",
        "isActive?",
    ];
    static defaultProps = {
        counter: 0,
        muted: 0,
    };
    static template = "mail.NotificationItem";

    setup() {
        super.setup();
        this.isToday = isToday;
        this.DateTime = DateTime;
        this.ui = useState(useService("ui"));
        this.markAsReadRef = useRef("markAsRead");
        this.rootHover = useHover("root");
    }

    get dateText() {
        if (isToday(this.props.datetime)) {
            return this.props.datetime?.toLocaleString(DateTime.TIME_SIMPLE);
        }
        return this.props.datetime?.toLocaleString(DateTime.DATE_MED);
    }

    onClick(ev) {
        this.props.onClick(ev.target === this.markAsReadRef.el);
    }
}
