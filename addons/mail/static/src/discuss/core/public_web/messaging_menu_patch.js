import { MessagingMenu } from "@mail/core/public_web/messaging_menu";

import { patch } from "@web/core/utils/patch";

patch(MessagingMenu.prototype, {
    /** @override */
    markAsRead(thread) {
        super.markAsRead(...arguments);
        if (thread.model === "discuss.channel") {
            thread.markAsRead();
        }
    },
});
