/** @odoo-module */

import { browser } from "@web/core/browser/browser";
import { ChatWindow } from "@mail/web/chat_window/chat_window_model";
import { assignDefined } from "@mail/utils/misc";
import { registry } from "@web/core/registry";

export const CHAT_WINDOW_END_GAP_WIDTH = 10; // for a single end, multiply by 2 for left and right together.
export const CHAT_WINDOW_INBETWEEN_WIDTH = 5;
export const CHAT_WINDOW_WIDTH = 340;
export const CHAT_WINDOW_HIDDEN_WIDTH = 55;

export class ChatWindowService {
    constructor(env, services) {
        this.env = env;
        /** @type {import("@mail/core/store_service").Store} */
        this.store = services["mail.store"];
        this.orm = services.orm;
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
        return this.store.chatWindows.filter((chatWindow) => !chatWindow.hidden);
    }

    get hidden() {
        return this.store.chatWindows.filter((chatWindow) => chatWindow.hidden);
    }

    get maxVisible() {
        const startGap = this.store.isSmall
            ? 0
            : this.hidden.length > 0
            ? CHAT_WINDOW_END_GAP_WIDTH + CHAT_WINDOW_HIDDEN_WIDTH
            : CHAT_WINDOW_END_GAP_WIDTH;
        const endGap = this.store.isSmall ? 0 : CHAT_WINDOW_END_GAP_WIDTH;
        const available = browser.innerWidth - startGap - endGap;
        const maxAmountWithoutHidden = Math.floor(
            available / (CHAT_WINDOW_WIDTH + CHAT_WINDOW_INBETWEEN_WIDTH)
        );
        return maxAmountWithoutHidden;
    }

    notifyState(chatWindow) {
        if (this.env.isSmall) {
            return;
        }
        if (chatWindow.thread?.model === "discuss.channel") {
            return this.orm.silent.call(
                "discuss.channel",
                "channel_fold",
                [[chatWindow.thread.id]],
                {
                    state: chatWindow.thread.state,
                }
            );
        }
    }

    /**
     * @param {ChatWindowData} [data]
     * @returns {ChatWindow}
     */
    insert(data = {}) {
        const chatWindow = this.store.chatWindows.find(
            (c) => c.threadLocalId === data.thread?.localId
        );
        if (!chatWindow) {
            const chatWindow = new ChatWindow(this.store, data);
            assignDefined(chatWindow, data);
            let index;
            if (!data.replaceNewMessageChatWindow) {
                if (this.maxVisible <= this.store.chatWindows.length) {
                    const swaped = this.visible[this.visible.length - 1];
                    index = this.visible.length - 1;
                    this.hide(swaped);
                } else {
                    index = this.store.chatWindows.length;
                }
            } else {
                const newMessageChatWindowIndex = this.store.chatWindows.findIndex(
                    (chatWindow) => !chatWindow.thread
                );
                index =
                    newMessageChatWindowIndex !== -1
                        ? newMessageChatWindowIndex
                        : this.store.chatWindows.length;
            }
            this.store.chatWindows.splice(
                index,
                data.replaceNewMessageChatWindow ? 1 : 0,
                chatWindow
            );
            return this.store.chatWindows[index]; // return reactive version
        }
        assignDefined(chatWindow, data);
        return chatWindow;
    }

    focus(chatWindow) {
        chatWindow.autofocus++;
    }

    makeVisible(chatWindow) {
        const swaped = this.visible[this.visible.length - 1];
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

    async close(chatWindow, { escape = false } = {}) {
        if (this.store.isSmall && !this.store.discuss.isActive) {
            // If we are in mobile and discuss is not open, it means the
            // chat window was opened from the messaging menu. In that
            // case it should be re-opened to simulate it was always
            // there in the background.
            document.querySelector(".o_menu_systray i[aria-label='Messages']").click();
            // ensure messaging menu is opened before chat window is closed
            await Promise.resolve();
        }
        if (this.maxVisible < this.store.chatWindows.length) {
            const swaped = this.hidden[0];
            swaped.hidden = false;
            swaped.folded = false;
        }
        const index = this.store.chatWindows.findIndex((c) => c === chatWindow);
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
    dependencies: ["mail.store", "orm"],
    start(env, services) {
        return new ChatWindowService(env, services);
    },
};

registry.category("services").add("mail.chat_window", chatWindowService);
