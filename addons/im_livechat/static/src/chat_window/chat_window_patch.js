/* @odoo-module */

import { ChatWindow } from "@mail/core/common/chat_window";

import { patch } from "@web/core/utils/patch";

patch(ChatWindow.prototype, {
    close(options) {
        super.close(options);
        if (
            this.thread?.type === "livechat" &&
            this.thread.isLoaded &&
            this.thread.messages.length === 0
        ) {
            this.threadService.unpin(this.thread);
        }
    },
});
