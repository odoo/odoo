/* @odoo-module */

import { Record, modelRegistry } from "@mail/core/common/record";
import { assignDefined } from "@mail/utils/common/misc";

import { _t } from "@web/core/l10n/translation";
import { browser } from "@web/core/browser/browser";

export const CHAT_WINDOW_END_GAP_WIDTH = 10; // for a single end, multiply by 2 for left and right together.
export const CHAT_WINDOW_INBETWEEN_WIDTH = 5;
export const CHAT_WINDOW_WIDTH = 360; // same value as $o-mail-ChatWindow-width
export const CHAT_WINDOW_HIDDEN_WIDTH = 55;

/** @typedef {{ thread?: import("@mail/core/common/thread_model").Thread, folded?: boolean, replaceNewMessageChatWindow?: boolean }} ChatWindowData */

export class ChatWindow extends Record {
    static ids = ["threadLocalId"];
    /** @type {ChatWindow[]} */
    static records = [];

    static get hidden() {
        return this.records.filter((chatWindow) => chatWindow.hidden);
    }

    static get maxVisible() {
        const startGap = this.env.services.ui.isSmall
            ? 0
            : this.hidden.length > 0
            ? CHAT_WINDOW_END_GAP_WIDTH + CHAT_WINDOW_HIDDEN_WIDTH
            : CHAT_WINDOW_END_GAP_WIDTH;
        const endGap = this.env.services.ui.isSmall ? 0 : CHAT_WINDOW_END_GAP_WIDTH;
        const available = browser.innerWidth - startGap - endGap;
        const maxAmountWithoutHidden = Math.max(
            1,
            Math.floor(available / (CHAT_WINDOW_WIDTH + CHAT_WINDOW_INBETWEEN_WIDTH))
        );
        return maxAmountWithoutHidden;
    }

    static get visible() {
        return this.records.filter((chatWindow) => !chatWindow.hidden);
    }

    static hide(chatWindow) {
        chatWindow.hidden = true;
        chatWindow.folded = true;
        chatWindow.thread.state = "folded";
    }

    /**
     * @param {ChatWindowData} [data]
     * @returns {ChatWindow}
     */
    static insert(data = {}) {
        const chatWindow = this.records.find((c) => c.threadLocalId === data.thread?.localId);
        if (!chatWindow) {
            const chatWindow = new ChatWindow(this.store, data);
            assignDefined(chatWindow, data);
            let index;
            if (!data.replaceNewMessageChatWindow) {
                if (this.maxVisible <= this.records.length) {
                    const swaped = this.visible[this.visible.length - 1];
                    index = this.visible.length - 1;
                    this.hide(swaped);
                } else {
                    index = this.records.length;
                }
            } else {
                const newMessageCWIndex = this.records.findIndex((cw) => !cw.thread);
                index = newMessageCWIndex !== -1 ? newMessageCWIndex : this.records.length;
            }
            this.records.splice(index, data.replaceNewMessageChatWindow ? 1 : 0, chatWindow);
            return this.records[index]; // return reactive version
        }
        if (chatWindow.hidden) {
            this.makeVisible(chatWindow);
        }
        assignDefined(chatWindow, data);
        return chatWindow;
    }

    makeVisible(chatWindow) {
        const swaped = this.visible[this.visible.length - 1];
        this.hide(swaped);
        this.show(chatWindow);
    }

    show(chatWindow) {
        chatWindow.hidden = false;
        chatWindow.folded = false;
        chatWindow.thread.state = "open";
    }

    /** @type {import("@mail/core/common/store_service").Store} */
    _store;

    /** @type {import("@mail/core/common/thread_model").Thread.localId} */
    threadLocalId;
    autofocus = 0;
    folded = false;
    hidden = false;

    /**
     * @param {import("@mail/core/common/store_service").Store store
     * @param {ChatWindowData} data
     * @returns {ChatWindow}
     */
    constructor(store, data) {
        super(store, data);
        Object.assign(this, {
            thread: data.thread,
            _store: store,
        });
    }

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

modelRegistry.add(ChatWindow.name, ChatWindow);
