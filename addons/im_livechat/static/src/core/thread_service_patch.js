/* @odoo-module */

import { ThreadService } from "@mail/core/common/thread_service";
import { removeFromArray } from "@mail/utils/common/arrays";
import { assignDefined, createLocalId } from "@mail/utils/common/misc";

import { patch } from "@web/core/utils/patch";

patch(ThreadService.prototype, "im_livechat", {
    insert(data) {
        const isUnknown = !(createLocalId(data.model, data.id) in this.store.threads);
        const thread = this._super(data);
        if (thread.type === "livechat") {
            if (data?.channel) {
                assignDefined(thread, data.channel, ["anonymous_name"]);
            }
            if (isUnknown) {
                this.store.discuss.livechat.threads.push(thread.localId);
                this.sortChannels();
            }
        }
        return thread;
    },
    /**
     * @override
     * @param {import("@mail/core/common/thread_model").Thread} thread
     * @param {boolean} pushState
     */
    setDiscussThread(thread, pushState) {
        this._super(thread, pushState);
        if (this.ui.isSmall && thread.type === "livechat") {
            this.store.discuss.activeTab = "livechat";
        }
    },
    remove(thread) {
        if (thread.type === "livechat") {
            removeFromArray(this.store.discuss.livechat.threads, thread.localId);
        }
        this._super(thread);
    },

    canLeave(thread) {
        return thread.type !== "livechat" && this._super(thread);
    },

    canUnpin(thread) {
        if (thread.type === "livechat") {
            return thread.message_unread_counter === 0;
        }
        return this._super(thread);
    },

    getCounter(thread) {
        if (thread.type === "livechat") {
            return thread.message_unread_counter;
        }
        return this._super(thread);
    },

    sortChannels() {
        this._super();
        // Live chats are sorted by most recent interest date time in the sidebar.
        this.store.discuss.livechat.threads.sort((localId_1, localId_2) => {
            const thread1 = this.store.threads[localId_1];
            const thread2 = this.store.threads[localId_2];
            return thread2.lastInterestDateTime?.ts - thread1.lastInterestDateTime?.ts;
        });
    },

    /**
     * @returns {boolean} Whether the livechat thread changed.
     */
    goToOldestUnreadLivechatThread() {
        const oldestUnreadThread =
            this.store.threads[
                Object.values(this.store.discuss.livechat.threads)
                    .filter((localId) => this.store.threads[localId].isUnread)
                    .sort(
                        (localId_1, localId_2) =>
                            this.store.threads[localId_1].lastInterestDateTime?.ts -
                            this.store.threads[localId_2].lastInterestDateTime?.ts
                    )[0]
            ];
        if (!oldestUnreadThread) {
            return false;
        }
        if (this.store.discuss.isActive) {
            this.setDiscussThread(oldestUnreadThread);
            return true;
        }
        const chatWindow = this.chatWindowService.insert({ thread: oldestUnreadThread });
        if (chatWindow.hidden) {
            this.chatWindowService.makeVisible(chatWindow);
        } else if (chatWindow.folded) {
            this.chatWindowService.toggleFold(chatWindow);
        }
        this.chatWindowService.focus(chatWindow);
        return true;
    },
});
