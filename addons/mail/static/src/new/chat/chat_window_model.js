/* @odoo-module */

/** @typedef {{ thread?: import("@mail/new/core/thread_model").Thread, folded?: boolean, replaceNewMessageChatWindow?: boolean }} ChatWindowData */

import { _t } from "@web/core/l10n/translation";

export class ChatWindow {
    /** @type {import("@mail/new/core/store_service").Store} */
    _store;

    /** @type {import("@mail/new/core/thread_model").Thread.localId} */
    threadLocalId;
    autofocus = 0;
    folded = false;
    hidden = false;

    /**
     * @param {import("@mail/new/core/store_service").Store} store
     * @param {ChatWindowData} data
     * @returns {ChatWindow}
     */
    constructor(store, data) {
        Object.assign(this, {
            thread: data.thread,
            _store: store,
        });
    }

    get thread() {
        return this._store.threads[this.threadLocalId];
    }

    set thread(thread) {
        this.threadLocalId = thread?.localId;
    }

    get displayName() {
        return this.thread?.displayName ?? _t("New message");
    }
}
