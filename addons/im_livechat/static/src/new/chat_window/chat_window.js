/** @odoo-module */

import { ChatWindow } from "@mail/new/web/chat_window/chat_window";
import { patch } from "@web/core/utils/patch";

patch(ChatWindow.prototype, "im_livechat", {
    close(options) {
        this._super(options);
        if (
            this.thread?.type === "livechat" &&
            this.thread.isLoaded &&
            this.thread.messages.length === 0
        ) {
            this.threadService.unpin(this.thread);
        }
    },
});
