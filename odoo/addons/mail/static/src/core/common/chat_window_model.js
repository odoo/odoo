/* @odoo-module */

import { Record } from "@mail/core/common/record";
import { assignDefined } from "@mail/utils/common/misc";

import { _t } from "@web/core/l10n/translation";

/** @typedef {{ thread?: import("models").Thread, folded?: boolean, replaceNewMessageChatWindow?: boolean }} ChatWindowData */

export class ChatWindow extends Record {
    static id = "thread";
    /** @type {Object<number, import("models").ChatWindow} */
    static records = {};
    /** @returns {import("models").ChatWindow} */
    static get(data) {
        return super.get(data);
    }
    /** @returns {import("models").ChatWindow|import("models").ChatWindow[]} */
    static insert() {
        return super.insert(...arguments);
    }
    /**
     * @param {ChatWindowData} [data]
     * @returns {import("models").ChatWindow}
     */
    static _insert(data = {}) {
        const chatWindow = this.store.discuss.chatWindows.find((c) => c.thread?.eq(data.thread));
        if (!chatWindow) {
            /** @type {import("models").ChatWindow} */
            const chatWindow = this.preinsert(data);
            assignDefined(chatWindow, data);
            let index;
            const visible = this.env.services["mail.chat_window"].visible;
            const maxVisible = this.env.services["mail.chat_window"].maxVisible;
            if (!data.replaceNewMessageChatWindow) {
                if (maxVisible <= this.store.discuss.chatWindows.length) {
                    const swaped = visible[visible.length - 1];
                    index = visible.length - 1;
                    this.env.services["mail.chat_window"].hide(swaped);
                } else {
                    index = this.store.discuss.chatWindows.length;
                }
            } else {
                const newMessageChatWindowIndex = this.store.discuss.chatWindows.findIndex(
                    (cw) => !cw.thread
                );
                index =
                    newMessageChatWindowIndex !== -1
                        ? newMessageChatWindowIndex
                        : this.store.discuss.chatWindows.length;
            }
            this.store.discuss.chatWindows.splice(
                index,
                data.replaceNewMessageChatWindow ? 1 : 0,
                chatWindow
            );
            return chatWindow; // return reactive version
        }
        if (chatWindow.hidden) {
            this.env.services["mail.chat_window"].makeVisible(chatWindow);
        }
        assignDefined(chatWindow, data);
        return chatWindow;
    }

    thread = Record.one("Thread");
    autofocus = 0;
    folded = false;
    hidden = false;
    openMessagingMenuOnClose = false;

    get displayName() {
        return this.thread?.displayName ?? _t("New message");
    }

    get isOpen() {
        return !this.folded && !this.hidden;
    }
}

ChatWindow.register();
