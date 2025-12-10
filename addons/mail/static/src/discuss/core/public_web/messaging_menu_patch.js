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
    canUnpinItem(thread) {
        return thread.channel?.canUnpin && thread.self_member_id?.message_unread_counter === 0;
    },
    onSwipeLeftThreadNotification(thread) {
        const res = super.onSwipeLeftThreadNotification(...arguments);
        if (this.hasTouch() && this.canUnpinItem(thread)) {
            return {
                ...res,
                action: () => thread.unpin(),
                icon: "fa-times-circle",
                bgColor: "bg-danger",
            };
        }
        return res;
    },
});
