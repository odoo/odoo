/** @odoo-module */

import { ThreadService, threadService } from "@mail/new/core/thread_service";

import { patch } from "@web/core/utils/patch";

patch(ThreadService.prototype, "mail/web", {
    setup(env, services) {
        this._super(env, services);
        /** @type {import("@mail/new/chat/chat_window_service").ChatWindowService} */
        this.chatWindowService = services["mail.chat_window"];
    },
    open(thread, replaceNewMessageChatWindow) {
        if (!this.store.discuss.isActive || this.store.isSmall) {
            const chatWindow = this.chatWindowService.insert({
                folded: false,
                thread,
                replaceNewMessageChatWindow,
            });
            chatWindow.autofocus++;
            if (thread) {
                thread.state = "open";
            }
            this.chatWindowService.notifyState(chatWindow);
            return;
        }
        this._super(thread, replaceNewMessageChatWindow);
    },
});

patch(threadService, "mail/web", {
    dependencies: [...threadService.dependencies, "mail.chat_window"],
});
