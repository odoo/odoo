/* @odoo-module */

import { Record } from "@mail/core/common/record";
import { assignDefined } from "@mail/utils/common/misc";

import { _t } from "@web/core/l10n/translation";

/** @typedef {{ thread?: import("models").Thread, folded?: boolean, replaceNewMessageChatWindow?: boolean }} ChatWindowData */

export class ChatWindow extends Record {
    static id = "thread";
    /** @type {import("models").ChatWindow[]} */
    static records = [];
    /** @returns {import("models").ChatWindow} */
    static new(data) {
        return super.new(data);
    }
    /** @returns {import("models").ChatWindow} */
    static get(data) {
        return super.get(data);
    }
    /**
     * @param {ChatWindowData} [data]
     * @returns {import("models").ChatWindow}
     */
    static insert(data = {}) {
        const chatWindow = this.records.find((c) => c.thread?.eq(data.thread));
        if (!chatWindow) {
            const chatWindow = this.new(data);
            Object.assign(chatWindow, { thread: data.thread });
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

    thread = Record.one("Thread");
    autofocus = 0;
    folded = false;
    hidden = false;

    get displayName() {
        return this.thread?.displayName ?? _t("New message");
    }

    get isOpen() {
        return !this.folded && !this.hidden;
    }
}

ChatWindow.register();
