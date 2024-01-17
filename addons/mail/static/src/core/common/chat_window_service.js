/* @odoo-module */

import { assignDefined } from "@mail/utils/common/misc";

import { browser } from "@web/core/browser/browser";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";

export const CHAT_WINDOW_END_GAP_WIDTH = 10; // for a single end, multiply by 2 for left and right together.
export const CHAT_WINDOW_INBETWEEN_WIDTH = 5;
export const CHAT_WINDOW_WIDTH = 360; // same value as $o-mail-ChatWindow-width
export const CHAT_WINDOW_HIDDEN_WIDTH = 55;

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

    notifyState(chatWindow) {
        if (this.ui.isSmall || chatWindow.thread?.isTransient) {
            return;
        }
        if (chatWindow.thread?.model === "discuss.channel") {
            chatWindow.thread.foldStateCount++;
            return rpc(
                "/discuss/channel/fold",
                {
                    channel_id: chatWindow.thread.id,
                    state: chatWindow.thread.state,
                    state_count: chatWindow.thread.foldStateCount,
                },
                { shadow: true }
            );
        }
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
        this.notifyState(chatWindow);
        return chatWindow;
    }

    openNewMessage({ openMessagingMenuOnClose } = {}) {
        if (this.store.discuss.chatWindows.some(({ thread }) => !thread)) {
            // New message chat window is already opened.
            return;
        }
        this.store.ChatWindow.insert(assignDefined({}, { openMessagingMenuOnClose }));
    }

    closeNewMessage() {
        const newMessageChatWindow = this.store.discuss.chatWindows.find(({ thread }) => !thread);
        if (newMessageChatWindow) {
            this.close(newMessageChatWindow);
        }
    }

    get visible() {
        return this.store.discuss.chatWindows.filter((chatWindow) => !chatWindow.hidden);
    }

    get hidden() {
        return this.store.discuss.chatWindows.filter((chatWindow) => chatWindow.hidden);
    }

    get maxVisible() {
        const startGap = this.ui.isSmall
            ? 0
            : this.hidden.length > 0
            ? CHAT_WINDOW_END_GAP_WIDTH + CHAT_WINDOW_HIDDEN_WIDTH
            : CHAT_WINDOW_END_GAP_WIDTH;
        const endGap = this.ui.isSmall ? 0 : CHAT_WINDOW_END_GAP_WIDTH;
        const available = browser.innerWidth - startGap - endGap;
        const maxAmountWithoutHidden = Math.max(
            1,
            Math.floor(available / (CHAT_WINDOW_WIDTH + CHAT_WINDOW_INBETWEEN_WIDTH))
        );
        return maxAmountWithoutHidden;
    }

    focus(chatWindow) {
        chatWindow.autofocus++;
    }

    makeVisible(chatWindow) {
        const swaped = this.visible[this.visible.length - 1];
        this.hide(swaped);
        this.show(chatWindow, { notifyState: false });
    }

    toggleFold(chatWindow) {
        chatWindow.folded = !chatWindow.folded;
        const thread = chatWindow.thread;
        if (thread) {
            thread.state = chatWindow.folded ? "folded" : "open";
        }
        this.notifyState(chatWindow);
    }

    show(chatWindow, { notifyState = true } = {}) {
        chatWindow.hidden = false;
        chatWindow.folded = false;
        chatWindow.thread.state = "open";
        if (notifyState) {
            this.notifyState(chatWindow);
        }
    }

    hide(chatWindow) {
        chatWindow.hidden = true;
    }

    async close(chatWindow, options = {}) {
        const { escape = false } = options;
        if (!chatWindow.hidden && this.maxVisible < this.store.discuss.chatWindows.length) {
            const swaped = this.hidden[0];
            swaped.hidden = false;
            swaped.folded = false;
        }
        const index = this.store.discuss.chatWindows.findIndex((c) => c.eq(chatWindow));
        if (index > -1) {
            this.store.discuss.chatWindows.splice(index, 1);
        }
        const thread = chatWindow.thread;
        if (thread) {
            thread.state = "closed";
        }
        if (escape && this.store.discuss.chatWindows.length > 0) {
            this.focus(this.store.discuss.chatWindows.at(index - 1));
        }
        await this._onClose(chatWindow, options);
        chatWindow.delete();
    }
    async _onClose(chatWindow, { notifyState = true } = {}) {
        if (notifyState) {
            this.notifyState(chatWindow);
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
