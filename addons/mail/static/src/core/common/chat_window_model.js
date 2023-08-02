/* @odoo-module */

import { _t } from "@web/core/l10n/translation";

/** @typedef {{ thread?: import("@mail/core/common/thread_model").Thread, folded?: boolean, replaceNewMessageChatWindow?: boolean }} ChatWindowData */

export class ChatWindow {
    /** @type {import("@mail/core/common/store_service").Store} */
    _store;

    /** @type {import("@mail/core/common/thread_model").Thread.objectId} */
    threadObjectId;
    autofocus = 0;
    folded = false;
    hidden = false;

    /**
     * @param {import("@mail/core/common/store_service").Store} store
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
        return this._store.threads[this.threadObjectId];
    }

    set thread(thread) {
        this.threadObjectId = thread?.objectId;
    }

    get displayName() {
        return this.thread?.displayName ?? _t("New message");
    }

    get isOpen() {
        return !this.folded && !this.hidden;
    }
}
