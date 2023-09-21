/* @odoo-module */

import { DEFAULT_AVATAR } from "@mail/core/common/persona_service";
import { ThreadService } from "@mail/core/common/thread_service";
import { removeFromArray } from "@mail/utils/common/arrays";

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
    remove(thread) {
        if (thread.type === "livechat") {
            removeFromArray(this.store.discuss.livechat.threads, thread.localId);
        }
        super.remove(thread);
    },

    canLeave(thread) {
        return thread.type !== "livechat" && super.canLeave(thread);
    },

    canUnpin(thread) {
        if (thread.type === "livechat") {
            return thread.message_unread_counter === 0;
        }
        return super.canUnpin(thread);
    },

    getCounter(thread) {
        if (thread.type === "livechat") {
            return thread.message_unread_counter;
        }
        return super.getCounter(thread);
    },

    sortChannels() {
        super.sortChannels();
        // Live chats are sorted by most recent interest date time in the sidebar.
        this.store.discuss.livechat.threads.sort((localId_1, localId_2) => {
            const thread1 = this.store.Thread.records[localId_1];
            const thread2 = this.store.Thread.records[localId_2];
            return thread2.lastInterestDateTime?.ts - thread1.lastInterestDateTime?.ts;
        });
    },

    /**
     * @returns {boolean} Whether the livechat thread changed.
     */
    goToOldestUnreadLivechatThread() {
        const oldestUnreadThread =
            this.store.Thread.records[
                Object.values(this.store.discuss.livechat.threads)
                    .filter((localId) => this.store.Thread.records[localId].isUnread)
                    .sort(
                        (localId_1, localId_2) =>
                            this.store.Thread.records[localId_1].lastInterestDateTime?.ts -
                            this.store.Thread.records[localId_2].lastInterestDateTime?.ts
                    )[0]
            ];
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

    /**
     * @param {import("models").Persona} persona
     * @param {import("models").Thread} thread
     */
    avatarUrl(author, thread) {
        if (thread?.type === "livechat" && author?.type === "guest") {
            return DEFAULT_AVATAR;
        }
        return super.avatarUrl(author, thread);
    },
});
