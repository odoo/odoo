/* @odoo-module */

import { registry } from "@web/core/registry";

export class ChatWindowService {
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    constructor(env, services) {
        this.setup(env, services);
    }

    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    setup(env, services) {
        this.env = env;
        this.store = services["mail.store"];
        this.orm = services.orm;
        this.ui = services.ui;
    }

    open(thread, replaceNewMessageChatWindow) {
        const chatWindow = this.insert({
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
        if (this.store.chatWindows.some(({ thread }) => !thread)) {
            // New message chat window is already opened.
            return;
        }
        this.insert();
    }

    closeNewMessage() {
        const newMessageChatWindow = this.store.chatWindows.find(({ thread }) => !thread);
        if (newMessageChatWindow) {
            this.close(newMessageChatWindow);
        }
    }

    get visible() {
        return this.store.ChatWindow.visible;
    }

    get hidden() {
        return this.store.ChatWindow.hidden;
    }

    get maxVisible() {
        return this.store.ChatWindow.maxVisible;
    }

    /**
     * @param {ChatWindowData} [data]
     * @returns {ChatWindow}
     */
    insert(data) {
        return this.store.ChatWindow.insert(data);
    }

    focus(chatWindow) {
        chatWindow.autofocus++;
    }

    makeVisible(chatWindow) {
        this.store.ChatWindow.makeVisible(chatWindow);
    }

    toggleFold(chatWindow) {
        chatWindow.folded = !chatWindow.folded;
        const thread = chatWindow.thread;
        if (thread) {
            thread.state = chatWindow.folded ? "folded" : "open";
        }
    }

    show(chatWindow) {
        this.store.ChatWindow.show(chatWindow);
    }

    hide(chatWindow) {
        this.store.ChatWindow.hide(chatWindow);
    }

    close(chatWindow, { escape = false } = {}) {
        if (!chatWindow.hidden && this.maxVisible < this.store.chatWindows.length) {
            const swaped = this.hidden[0];
            swaped.hidden = false;
            swaped.folded = false;
        }
        const index = this.store.chatWindows.findIndex((c) => c.eq(chatWindow));
        if (index > -1) {
            this.store.chatWindows.splice(index, 1);
        }
        const thread = chatWindow.thread;
        if (thread) {
            thread.state = "closed";
        }
        if (escape && this.store.chatWindows.length > 0) {
            this.focus(this.store.chatWindows[index - 1]);
        }
    }
}

export const chatWindowService = {
    dependencies: ["mail.store", "orm", "ui"],
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    start(env, services) {
        return new ChatWindowService(env, services);
    },
};

registry.category("services").add("mail.chat_window", chatWindowService);
