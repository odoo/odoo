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
            }
        }
        return thread;
    },

    remove(thread) {
        if (thread.type === "livechat") {
            removeFromArray(this.store.discuss.livechat.threads, thread.localId);
        }
        this._super(thread);
    },

    canLeave(thread) {
        if (thread.type === "livechat" && this.localMessageUnreadCounter(thread) === 0) {
            return true;
        }
        return this._super(thread);
    },

    getCounter(thread) {
        if (thread.type === "livechat") {
            return this.localMessageUnreadCounter(thread);
        }
        return this._super(thread);
    },
});
