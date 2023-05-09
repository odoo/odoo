/** @odoo-module */

import { Thread } from "@mail/core/thread_model";
import { ThreadService } from "@mail/core/thread_service";
import { removeFromArray } from "@mail/utils/arrays";
import { assignDefined, createLocalId } from "@mail/utils/misc";
import { patch } from "@web/core/utils/patch";

patch(ThreadService.prototype, "im_livechat", {
    setup(env, services) {
        this._super(env, services);
        const store = services["mail.store"];
        patch(Thread.prototype, "im_livechat", {
            get canLeave() {
                return this.type !== "livechat" && this._super();
            },
            get canUnpin() {
                if (this.type === "livechat") {
                    return this.message_unread_counter === 0;
                }
                return this._super();
            },
            getCounter() {
                if (this.type === "livechat") {
                    return this.message_unread_counter;
                }
                return this._super();
            },
            remove() {
                if (this.type === "livechat") {
                    removeFromArray(store.discuss.livechat.threads, this.localId);
                }
                this._super();
            },
        });
    },
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
     * @param {import("@mail/core/thread_model").Thread} thread
     * @param {boolean} pushState
     */
    setDiscussThread(thread, pushState) {
        this._super(thread, pushState);
        if (this.store.isSmall && thread.type === "livechat") {
            this.store.discuss.activeTab = "livechat";
        }
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
