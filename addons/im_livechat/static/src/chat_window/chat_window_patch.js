/* @odoo-module */

import { ChatWindow } from "@mail/core/common/chat_window";
import { unpinThread } from "@mail/core/common/thread_service";

import { patch } from "@web/core/utils/patch";

patch(ChatWindow.prototype, "im_livechat", {
    close(options) {
        this._super(options);
        if (
            this.thread?.type === "livechat" &&
            this.thread.isLoaded &&
            this.thread.messages.length === 0
        ) {
            unpinThread(this.thread);
        }
    },
});
