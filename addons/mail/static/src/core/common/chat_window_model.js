/* @odoo-module */

import {
    DiscussModel,
    DiscussModelManager,
    discussModelRegistry,
} from "@mail/core/common/discuss_model";
import { assignDefined } from "@mail/utils/common/misc";

import { _t } from "@web/core/l10n/translation";
import {
    CHAT_WINDOW_END_GAP_WIDTH,
    CHAT_WINDOW_HIDDEN_WIDTH,
    CHAT_WINDOW_INBETWEEN_WIDTH,
    CHAT_WINDOW_WIDTH,
} from "./chat_window_service";
import { browser } from "@web/core/browser/browser";

/** @typedef {{ thread?: import("@mail/core/common/thread_model").Thread, folded?: boolean, replaceNewMessageChatWindow?: boolean }} ChatWindowData */

export class ChatWindow extends DiscussModel {
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
        super(store, data);
        Object.assign(this, {
            thread: data.thread,
            _store: store,
        });
    }

    get thread() {
        return this._store.Thread.records[this.threadObjectId];
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

export class ChatWindowManager extends DiscussModelManager {
    nextId = 0;
    /** @type {typeof ChatWindow} */
    class;
    /** @type {ChatWindow[]} */
    records = [];

    /**
     * @param {ChatWindowData} [data]
     * @returns {ChatWindow}
     */
    insert(data = {}) {
        const chatWindow = this.records.find((c) => c.threadObjectId === data.thread?.objectId);
        if (!chatWindow) {
            const chatWindow = new ChatWindow(this.store, data);
            chatWindow.objectId = this._createObjectId(data);
            assignDefined(chatWindow, data);
            let index;
            if (!data.replaceNewMessageChatWindow) {
                if (this.maxVisible <= this.records.length) {
                    const swaped = this.visible[this.visible.length - 1];
                    index = this.visible.length - 1;
                    this.env.services["mail.chat_window"].hide(swaped);
                } else {
                    index = this.records.length;
                }
            } else {
                const newMessageChatWindowIndex = this.records.findIndex(
                    (chatWindow) => !chatWindow.thread
                );
                index =
                    newMessageChatWindowIndex !== -1
                        ? newMessageChatWindowIndex
                        : this.records.length;
            }
            this.records.splice(index, data.replaceNewMessageChatWindow ? 1 : 0, chatWindow);
            return this.records[index]; // return reactive version
        }
        assignDefined(chatWindow, data);
        return chatWindow;
    }

    get visible() {
        return this.store.ChatWindow.records.filter((chatWindow) => !chatWindow.hidden);
    }

    get hidden() {
        return this.store.ChatWindow.records.filter((chatWindow) => chatWindow.hidden);
    }

    get maxVisible() {
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
}

discussModelRegistry.add("ChatWindow", [ChatWindow, ChatWindowManager]);
