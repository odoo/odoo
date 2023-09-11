/* @odoo-module */

/** @typedef {{ thread?: import("@mail/core/thread_model").Thread, folded?: boolean, replaceNewMessageChatWindow?: boolean }} ChatWindowData */

import { Record } from "@mail/core/record";
import { _t } from "@web/core/l10n/translation";

export class ChatWindow extends Record {
    /** @type {import("@mail/core/store_service").Store} */
    _store;

    /** @type {import("@mail/core/thread_model").Thread.localId} */
    threadLocalId;
    autofocus = 0;
    folded = false;
    hidden = false;

    /**
     * @param {import("@mail/core/store_service").Store} store
     * @param {ChatWindowData} data
     * @returns {ChatWindow}
     */
    constructor(store, data) {
        super();
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

    get isOpen() {
        return !this.folded && !this.hidden;
    }
}
