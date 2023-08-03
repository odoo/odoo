/* @odoo-module */

import { registry } from "@web/core/registry";

export const CHAT_WINDOW_END_GAP_WIDTH = 10; // for a single end, multiply by 2 for left and right together.
export const CHAT_WINDOW_INBETWEEN_WIDTH = 5;
export const CHAT_WINDOW_WIDTH = 360; // same value as $o-mail-ChatWindow-width
export const CHAT_WINDOW_HIDDEN_WIDTH = 55;

export class ChatWindowService {
    constructor(env, services) {
        this.setup(env, services);
    }

    setup(env, services) {
        this.env = env;
        /** @type {import("@mail/core/common/store_service").Store} */
        this.store = services["mail.store"];
        this.orm = services.orm;
        this.ui = services.ui;
    }

    open(thread, replaceNewMessageChatWindow) {
        const chatWindow = this.store.ChatWindow.insert({
            folded: false,
            thread,
            replaceNewMessageChatWindow,
        });
        chatWindow.autofocus++;
        if (thread) {
            thread.state = "open";
        }
        return chatWindow;
    }

    openNewMessage() {
        if (this.store.ChatWindow.records.some(({ thread }) => !thread)) {
            // New message chat window is already opened.
            return;
        }
        this.store.ChatWindow.insert();
    }

    closeNewMessage() {
        const newMessageChatWindow = this.store.ChatWindow.records.find(({ thread }) => !thread);
        if (newMessageChatWindow) {
            this.close(newMessageChatWindow);
        }
    }

    focus(chatWindow) {
        chatWindow.autofocus++;
    }

    makeVisible(chatWindow) {
        const swaped = this.store.ChatWindow.visible[this.store.ChatWindow.visible.length - 1];
        this.hide(swaped);
        this.show(chatWindow);
    }

    toggleFold(chatWindow) {
        chatWindow.folded = !chatWindow.folded;
        const thread = chatWindow.thread;
        if (thread) {
            thread.state = chatWindow.folded ? "folded" : "open";
        }
    }

    show(chatWindow) {
        chatWindow.hidden = false;
        chatWindow.folded = false;
        chatWindow.thread.state = "open";
    }

    hide(chatWindow) {
        chatWindow.hidden = true;
        chatWindow.folded = true;
        chatWindow.thread.state = "folded";
    }

    close(chatWindow, { escape = false } = {}) {
        if (this.store.ChatWindow.maxVisible < this.store.ChatWindow.records.length) {
            const swaped = this.store.ChatWindow.hidden[0];
            swaped.hidden = false;
            swaped.folded = false;
        }
        const index = this.store.ChatWindow.records.findIndex((c) => c.equals(chatWindow));
        if (index > -1) {
            this.store.ChatWindow.records.splice(index, 1);
        }
        const thread = chatWindow.thread;
        if (thread) {
            thread.state = "closed";
        }
        if (escape && this.store.ChatWindow.records.length > 0) {
            this.focus(this.store.ChatWindow.records[index - 1]);
        }
    }
}

export const chatWindowService = {
    dependencies: ["mail.store", "orm", "ui"],
    start(env, services) {
        return new ChatWindowService(env, services);
    },
};

registry.category("services").add("mail.chat_window", chatWindowService);
