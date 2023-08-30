/* @odoo-module */

import { Record } from "@mail/core/common/record";
import { assignDefined } from "@mail/utils/common/misc";

import { _t } from "@web/core/l10n/translation";

/** @typedef {{ thread?: import("@mail/core/common/thread_model").Thread, folded?: boolean, replaceNewMessageChatWindow?: boolean }} ChatWindowData */

export class ChatWindow extends Record {
    /** @type {ChatWindow[]} */
    static records = [];
    /**
     * @param {ChatWindowData} [data]
     * @returns {ChatWindow}
     */
    static insert(data = {}) {
        const chatWindow = this.records.find((c) => c.threadLocalId === data.thread?.localId);
        if (!chatWindow) {
            const chatWindow = new ChatWindow();
            Object.assign(chatWindow, {
                thread: data.thread,
                _store: this.store,
            });
            assignDefined(chatWindow, data);
            let index;
            const visible = this.env.services["mail.chat_window"].visible;
            const maxVisible = this.env.services["mail.chat_window"].maxVisible;
            if (!data.replaceNewMessageChatWindow) {
                if (maxVisible <= this.records.length) {
                    const swaped = visible[visible.length - 1];
                    index = visible.length - 1;
                    this.env.services["mail.chat_window"].hide(swaped);
                } else {
                    index = this.records.length;
                }
            } else {
                const newMessageChatWindowIndex = this.records.findIndex((cw) => !cw.thread);
                index =
                    newMessageChatWindowIndex !== -1
                        ? newMessageChatWindowIndex
                        : this.records.length;
            }
            this.records.splice(index, data.replaceNewMessageChatWindow ? 1 : 0, chatWindow);
            return this.records[index]; // return reactive version
        }
        if (chatWindow.hidden) {
            this.env.services["mail.chat_window"].makeVisible(chatWindow);
        }
        assignDefined(chatWindow, data);
        return chatWindow;
    }

    /** @type {import("@mail/core/common/store_service").Store} */
    _store;

    /** @type {import("@mail/core/common/thread_model").Thread.localId} */
    threadLocalId;
    autofocus = 0;
    folded = false;
    hidden = false;

    get thread() {
        return this._store.Thread.records[this.threadLocalId];
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

ChatWindow.register();
