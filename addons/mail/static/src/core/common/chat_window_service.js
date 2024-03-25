import { assignDefined, rpcWithEnv } from "@mail/utils/common/misc";

import { browser } from "@web/core/browser/browser";
/** @type {ReturnType<import("@mail/utils/common/misc").rpcWithEnv>} */
let rpc;
import { registry } from "@web/core/registry";

export const CHAT_WINDOW_END_GAP_WIDTH = 10; // for a single end, multiply by 2 for left and right together.
export const CHAT_WINDOW_INBETWEEN_WIDTH = 5;
export const CHAT_WINDOW_WIDTH = 360; // same value as $o-mail-ChatWindow-width
export const CHAT_WINDOW_HIDDEN_WIDTH = 55;
export const CHAT_BUBBLE_SIZE = 56; // same value as $o-mail-ChatBubble-medium
export const CHAT_BUBBLE_PADDING = 20; // container has 10px padding, multiply by 2 for left and right together.
export const CHAT_BUBBLE_LIMIT = 7;
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
        rpc = rpcWithEnv(env);
        this.env = env;
        this.store = services["mail.store"];
        this.orm = services.orm;
        this.ui = services.ui;
    }

    notifyState(target) {
        if (this.ui.isSmall || target.thread?.isTransient) {
            return;
        }
        if (target.thread?.model === "discuss.channel") {
            target.thread.foldStateCount++;
            return rpc(
                "/discuss/channel/fold",
                {
                    channel_id: target.thread.id,
                    state: target.thread.state,
                    state_count: target.thread.foldStateCount,
                },
                { shadow: true }
            );
        }
    }

    open(thread, replaceNewMessageChatWindow, { openMessagingMenuOnClose } = {}) {
        const chatWindow = this.store.ChatWindow.insert(
            assignDefined(
                {
                    folded: false,
                    replaceNewMessageChatWindow,
                    thread,
                },
                {
                    openMessagingMenuOnClose,
                }
            )
        );
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
        const chatBubblesWidth = CHAT_BUBBLE_SIZE + CHAT_BUBBLE_PADDING;
        const startGap = this.ui.isSmall
            ? 0
            : this.hidden.length > 0
            ? CHAT_WINDOW_END_GAP_WIDTH + CHAT_WINDOW_HIDDEN_WIDTH
            : CHAT_WINDOW_END_GAP_WIDTH;
        const endGap = this.ui.isSmall ? 0 : CHAT_WINDOW_END_GAP_WIDTH;
        const available = browser.innerWidth - startGap - endGap - chatBubblesWidth;
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
        if (!chatWindow.thread) {
            return this.closeNewMessage();
        }
        chatWindow.folded = !chatWindow.folded;
        const thread = chatWindow.thread;
        thread.state = chatWindow.folded ? "folded" : "open";
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
    async _onClose(target, { notifyState = true } = {}) {
        if (notifyState) {
            this.notifyState(target);
        }
    }

    async closeBubble(bubble, options = {}) {
        bubble.thread.state = "closed";
        await this._onClose(bubble, options);
        bubble.delete();
    }

    updateThreadDisplay(thread) {
        if (!this.store.usingChatBubbles) {
            return this.store.ChatWindow.insert({
                thread,
                folded: thread.state === "folded",
            });
        }
        if (thread.state === "open" && !this.ui.isSmall) {
            this.store.ChatBubble.get({ thread })?.delete();
            this.store.ChatWindow.insert({ thread });
        }
        if (thread.state === "folded") {
            this.store.ChatWindow.get({ thread })?.delete();
            this.store.ChatBubble.insert({ thread });
        }
    }

    get chatBubbleLimit() {
        const chatBubbleSpace = CHAT_BUBBLE_SIZE + CHAT_BUBBLE_PADDING;
        return Math.min(CHAT_BUBBLE_LIMIT, Math.floor(browser.innerHeight / chatBubbleSpace));
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
