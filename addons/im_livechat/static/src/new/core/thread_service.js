/** @odoo-module */

import { ThreadService } from "@mail/new/core/thread_service";
import { removeFromArray } from "@mail/new/utils/arrays";
import { assignDefined, createLocalId } from "@mail/new/utils/misc";
import { patch } from "@web/core/utils/patch";

patch(ThreadService.prototype, "im_livechat", {
    insert(data) {
        const isUnknown = !(createLocalId(data.model, data.id) in this.store.threads);
        const thread = this._super(data);
        if (thread.type === "livechat") {
            if (data.serverData?.channel) {
                assignDefined(thread, data.serverData.channel, ["anonymous_name"]);
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
     * @param {import("@mail/new/core/thread_model").Thread} thread
     */
    setDiscussThread(thread) {
        this._super(thread);
        if (this.store.isSmall && thread.type === "livechat") {
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
            return this.localMessageUnreadCounter(thread) === 0;
        }
        return this._super(thread);
    },

    getCounter(thread) {
        if (thread.type === "livechat") {
            return this.localMessageUnreadCounter(thread);
        }
        return this._super(thread);
    },

    sortChannels() {
        this._super();
        // Live chats are sorted by most recent interest date time in the sidebar.
        this.store.discuss.livechat.threads.sort((localId_1, localId_2) => {
            const thread1 = this.store.threads[localId_1];
            const thread2 = this.store.threads[localId_2];
            return thread2.lastInterestDateTime.ts - thread1.lastInterestDateTime.ts;
        });
    },
});
