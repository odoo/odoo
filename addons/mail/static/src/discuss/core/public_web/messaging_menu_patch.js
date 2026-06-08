import { MessagingMenu } from "@mail/core/public_web/messaging_menu";

import { patch } from "@web/core/utils/patch";

patch(MessagingMenu.prototype, {
    /** @override */
    markAsRead(thread) {
        super.markAsRead(...arguments);
        if (thread.channel) {
            thread.markAsRead();
        }
    },
    onSwipeLeftThreadNotification(thread) {
        const res = super.onSwipeLeftThreadNotification(...arguments);
        if (this.hasTouch() && thread.channel?.canHide) {
            return {
                ...res,
                action: () => thread.channel.unpinChannel(),
                icon: "fa-times-circle",
                bgColor: "bg-danger",
            };
        }
        return res;
    },
});
