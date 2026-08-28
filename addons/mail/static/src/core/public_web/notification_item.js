import { DiscussAvatar } from "@mail/core/common/discuss_avatar";
import { MessageSeenIndicator } from "@mail/discuss/core/common/message_seen_indicator";
import { useHover } from "@mail/utils/common/hooks";
import { useSubEnv } from "@web/owl2/utils";

import { Component, signal, t, useProps } from "@odoo/owl";

import { ActionSwiper, onSwipeType } from "@web/core/action_swiper/action_swiper";
import { useService } from "@web/core/utils/hooks";

const { DateTime } = luxon;

const isMarkAsRead = t.boolean();
const isMiddleClick = t.boolean();

export class NotificationItem extends Component {
    static components = { ActionSwiper, DiscussAvatar, MessageSeenIndicator };
    static template = "mail.NotificationItem";

    markAsReadRef = signal.ref();
    rootRef = signal.ref();

    setup() {
        super.setup();
        this.DateTime = DateTime;
        this.ui = useService("ui");
        this.store = useService("mail.store");
        this.props = useProps({
            className: t.string().optional(""),
            counter: t.number().optional(0),
            datetime: t.instanceOf(DateTime).optional(),
            hasMarkAsReadButton: t.boolean().optional(),
            iconSrc: t.string().optional(),
            important: t.or([t.boolean(), t.number()]).optional(),
            isActive: t.boolean().optional(),
            muted: t.number().optional(0),
            onClick: t.function([isMarkAsRead, isMiddleClick.optional()]),
            onSwipeLeft: onSwipeType.optional(),
            onSwipeRight: onSwipeType.optional(),
            persona: t
                .or([
                    t.instanceOf(this.store["res.partner"]),
                    t.instanceOf(this.store["mail.guest"]),
                ])
                .optional(),
            slots: t.object().optional(),
            textClassName: t.string().optional(""),
            thread: t.instanceOf(this.store["mail.thread"]).optional(),
        });
        this.rootHover = useHover(this.rootRef);
        useSubEnv({ inNotificationItem: true });
    }

    get dateText() {
        if (!this.props.datetime) {
            return "";
        }
        const startOfToday = this.store.startOfToday;
        if (this.props.datetime.hasSame(startOfToday, "day")) {
            return this.props.datetime.toLocaleString(DateTime.TIME_SIMPLE);
        }
        if (this.props.datetime.hasSame(startOfToday, "year")) {
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
            "o-interest": this.props.muted === 0,
            "opacity-50": this.props.muted === 2,
            "px-1 py-2 gap-1 o-small": this.ui.isSmall,
            "o-p-1_5 gap-2": !this.ui.isSmall,
            "o-active": this.props.isActive,
            [this.props.className]: this.props.className,
        };
    }

    onClick(ev, isMiddleClick) {
        this.props.onClick(this.markAsReadRef()?.contains(ev.target), isMiddleClick);
    }
}
