import { isToday } from "@mail/utils/common/dates";
import { useHover } from "@mail/utils/common/hooks";

import { Component, useRef, useSubEnv } from "@odoo/owl";

import { ActionSwiper } from "@web/core/action_swiper/action_swiper";
import { useService } from "@web/core/utils/hooks";

const { DateTime } = luxon;

export class NotificationItem extends Component {
    static components = { ActionSwiper };
    static props = [
        "counter?",
        "datetime?",
        "first?",
        "hasMarkAsReadButton?",
        "iconSrc?",
        "important?",
        "muted?",
        "onClick",
        "onSwipeLeft?",
        "onSwipeRight?",
        "slots?",
        "isActive?",
        "nameMaxLine?",
        "textMaxLine?",
        "thread?",
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
        this.ui = useService("ui");
        this.store = useService("mail.store");
        this.markAsReadRef = useRef("markAsRead");
        this.rootHover = useHover("root");
        useSubEnv({ inNotificationItem: true });
    }

    get dateText() {
        if (isToday(this.props.datetime)) {
            return this.props.datetime?.toLocaleString(DateTime.TIME_SIMPLE);
        }
        if (this.props.datetime?.year === DateTime.now().year) {
            return this.props.datetime?.toLocaleString({ month: "short", day: "numeric" });
        }
        return this.props.datetime?.toLocaleString(DateTime.DATE_MED);
    }

    onClick(ev) {
        this.props.onClick(this.markAsReadRef.el?.contains(ev.target));
    }

    webkitLineClamp(maxLine) {
        return `
            display: -webkit-box;
            overflow: hidden;
            -webkit-box-orient: vertical;
            -webkit-line-clamp: ${maxLine};
        `;
    }
}
