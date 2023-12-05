/* @odoo-module */

import { ThreadService } from "@mail/core/common/thread_service";

import { patch } from "@web/core/utils/patch";

patch(ThreadService.prototype, {
    /**
     * @override
     * @param {import("models").Thread} thread
     * @param {boolean} pushState
     */
    setDiscussThread(thread, pushState) {
        super.setDiscussThread(thread, pushState);
        if (this.ui.isSmall && thread.type === "livechat") {
            this.store.discuss.activeTab = "livechat";
        }
    },

    /** @deprecated */
    sortChannels() {
        super.sortChannels();
        // Live chats are sorted by most recent interest date time in the sidebar.
        this.store.discuss.livechat.threads.sort(
            (t1, t2) => t2.lastInterestDateTime?.ts - t1.lastInterestDateTime?.ts
        );
    },

    /**
     * @returns {boolean} Whether the livechat thread changed.
     */
    goToOldestUnreadLivechatThread() {
        const oldestUnreadThread = this.store.discuss.livechat.threads
            .filter((thread) => thread.isUnread)
            .sort((t1, t2) => t1.lastInterestDateTime?.ts - t2.lastInterestDateTime?.ts)[0];
        if (!oldestUnreadThread) {
            return false;
        }
        if (this.store.discuss.isActive) {
            this.setDiscussThread(oldestUnreadThread);
            return true;
        }
        const chatWindow = this.store.ChatWindow.insert({ thread: oldestUnreadThread });
        if (chatWindow.hidden) {
            this.chatWindowService.makeVisible(chatWindow);
        } else if (chatWindow.folded) {
            this.chatWindowService.toggleFold(chatWindow);
        }
        this.chatWindowService.focus(chatWindow);
        return true;
    },
});
