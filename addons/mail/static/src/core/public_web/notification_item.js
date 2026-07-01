import { DiscussAvatar } from "@mail/core/common/discuss_avatar";
import { MessageSeenIndicator } from "@mail/discuss/core/common/message_seen_indicator";
import { isToday } from "@mail/utils/common/dates";
import { useHover } from "@mail/utils/common/hooks";
import { useRef, useSubEnv } from "@web/owl2/utils";

import { Component, props, t } from "@odoo/owl";

import { ActionSwiper, onSwipeType } from "@web/core/action_swiper/action_swiper";
import { useService } from "@web/core/utils/hooks";

const { DateTime } = luxon;

const isMarkAsRead = t.boolean();

export class NotificationItem extends Component {
    static components = { ActionSwiper, DiscussAvatar, MessageSeenIndicator };
    static template = "mail.NotificationItem";

    setup() {
        super.setup();
        this.isToday = isToday;
        this.DateTime = DateTime;
        this.ui = useService("ui");
        this.store = useService("mail.store");
        this.props = props({
            counter: t.number().optional(0),
            datetime: t.instanceOf(DateTime).optional(),
            first: t.boolean().optional(),
            hasMarkAsReadButton: t.boolean().optional(),
            iconSrc: t.string().optional(),
            important: t.or([t.boolean(), t.number()]).optional(),
            isActive: t.boolean().optional(),
            muted: t.number().optional(0),
            nameMaxLine: t.number().optional(),
            onClick: t.function([isMarkAsRead]),
            onSwipeLeft: onSwipeType.optional(),
            onSwipeRight: onSwipeType.optional(),
            persona: t
                .or([
                    t.instanceOf(this.store["res.partner"].Class),
                    t.instanceOf(this.store["mail.guest"].Class),
                ])
                .optional(),
            slots: t.object().optional(),
            textMaxLine: t.number().optional(),
            thread: t.instanceOf(this.store["mail.thread"].Class).optional(),
        });
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

    get message() {
        return this.props.thread?.newestPersistentOfAllMessage;
    }

    get attClass() {
        return {
            "o-important": this.props.important,
            "o-interest border-secondary": this.props.muted === 0,
            "border-secondary": this.props.muted === 1,
            "opacity-50 border-secondary": this.props.muted === 2,
            "px-3 py-2 gap-1 o-small": this.ui.isSmall,
            "border-top-0": this.props.first,
            "o-px-2_5 o-py-1_5 gap-2": !this.ui.isSmall,
            "o-active": this.props.isActive,
        };
    }

    onClick(ev) {
        this.props.onClick(this.markAsReadRef.el?.contains(ev.target));
    }
}
