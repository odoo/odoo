/* @odoo-module */

import {
    ThreadService,
    canLeaveThread,
    canUnpinThread,
    getThreadCounter,
    insertThread,
    removeThread,
    setDiscussThread,
    sortChannels,
} from "@mail/core/common/thread_service";
import { removeFromArray } from "@mail/utils/common/arrays";
import { assignDefined, createLocalId } from "@mail/utils/common/misc";
import { patchFn } from "@mail/utils/common/patch";

import { patch } from "@web/core/utils/patch";

let store;
let ui;

patchFn(canLeaveThread, function (thread) {
    return thread.type !== "livechat" && this._super(thread);
});

patchFn(canUnpinThread, function (thread) {
    if (thread.type === "livechat") {
        return thread.message_unread_counter === 0;
    }
    return this._super(thread);
});

patchFn(getThreadCounter, function (thread) {
    if (thread.type === "livechat") {
        return thread.message_unread_counter;
    }
    return this._super(thread);
});

patchFn(insertThread, function (data) {
    const isUnknown = !(createLocalId(data.model, data.id) in store.threads);
    const thread = this._super(data);
    if (thread.type === "livechat") {
        if (data?.channel) {
            assignDefined(thread, data.channel, ["anonymous_name"]);
        }
        if (isUnknown) {
            store.discuss.livechat.threads.push(thread.localId);
            sortChannels();
        }
    }
    return thread;
});
patchFn(sortChannels, function () {
    this._super();
    // Live chats are sorted by most recent interest date time in the sidebar.
    store.discuss.livechat.threads.sort((localId_1, localId_2) => {
        const thread1 = store.threads[localId_1];
        const thread2 = store.threads[localId_2];
        return thread2.lastInterestDateTime.ts - thread1.lastInterestDateTime.ts;
    });
});
/**
 * @override
 * @param {import("@mail/core/common/thread_model").Thread} thread
 * @param {boolean} pushState
 */
patchFn(setDiscussThread, function (thread, pushState) {
    this._super(thread, pushState);
    if (ui.isSmall && thread.type === "livechat") {
        store.discuss.activeTab = "livechat";
    }
});

patchFn(removeThread, function (thread) {
    if (thread.type === "livechat") {
        removeFromArray(store.discuss.livechat.threads, thread.localId);
    }
    this._super(thread);
});

patch(ThreadService.prototype, "im_livechat", {
    setup(env, services) {
        this._super(...arguments);
        store = services["mail.store"];
        ui = services.ui;
    },
});
