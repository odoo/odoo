/* @odoo-module */

import { ChatWindow } from "@mail/core/common/chat_window_model";
import { assignDefined } from "@mail/utils/common/misc";
import { makeFnPatchable } from "@mail/utils/common/patch";

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";

export const CHAT_WINDOW_END_GAP_WIDTH = 10; // for a single end, multiply by 2 for left and right together.
export const CHAT_WINDOW_INBETWEEN_WIDTH = 5;
export const CHAT_WINDOW_WIDTH = 360; // same value as $o-mail-ChatWindow-width
export const CHAT_WINDOW_HIDDEN_WIDTH = 55;

let orm;
/** @type {import("@mail/core/common/store_service").Store} */
let store;
let ui;

export const closeChatWindow = makeFnPatchable(function (chatWindow, { escape = false } = {}) {
    if (getMaxVisibleChatWindows() < store.chatWindows.length) {
        const swaped = getHiddenChatWindows()[0];
        swaped.hidden = false;
        swaped.folded = false;
    }
    const index = store.chatWindows.findIndex((c) => c === chatWindow);
    if (index > -1) {
        store.chatWindows.splice(index, 1);
    }
    const thread = chatWindow.thread;
    if (thread) {
        thread.state = "closed";
    }
    if (escape && store.chatWindows.length > 0) {
        focusChatWindow(store.chatWindows[index - 1]);
    }
});

export function closeNewMessage() {
    const newMessageChatWindow = store.chatWindows.find(({ thread }) => !thread);
    if (newMessageChatWindow) {
        closeChatWindow(newMessageChatWindow);
    }
}

export function focusChatWindow(chatWindow) {
    chatWindow.autofocus++;
}

export function getHiddenChatWindows() {
    return store.chatWindows.filter((chatWindow) => chatWindow.hidden);
}

export function getMaxVisibleChatWindows() {
    const startGap = ui.isSmall
        ? 0
        : getHiddenChatWindows().length > 0
        ? CHAT_WINDOW_END_GAP_WIDTH + CHAT_WINDOW_HIDDEN_WIDTH
        : CHAT_WINDOW_END_GAP_WIDTH;
    const endGap = ui.isSmall ? 0 : CHAT_WINDOW_END_GAP_WIDTH;
    const available = browser.innerWidth - startGap - endGap;
    const maxAmountWithoutHidden = Math.floor(
        available / (CHAT_WINDOW_WIDTH + CHAT_WINDOW_INBETWEEN_WIDTH)
    );
    return maxAmountWithoutHidden;
}

export const getVisibleChatWindows = makeFnPatchable(function () {
    return store.chatWindows.filter((chatWindow) => !chatWindow.hidden);
});

export const hideChatWindow = makeFnPatchable(function (chatWindow) {
    chatWindow.hidden = true;
    chatWindow.folded = true;
    chatWindow.thread.state = "folded";
});

/**
 * @param {ChatWindowData} [data]
 * @returns {ChatWindow}
 */
export function insertChatWindow(data = {}) {
    const chatWindow = store.chatWindows.find((c) => c.threadLocalId === data.thread?.localId);
    if (!chatWindow) {
        const chatWindow = new ChatWindow(store, data);
        assignDefined(chatWindow, data);
        let index;
        if (!data.replaceNewMessageChatWindow) {
            if (getMaxVisibleChatWindows() <= store.chatWindows.length) {
                const swaped = getVisibleChatWindows()[getVisibleChatWindows().length - 1];
                index = getVisibleChatWindows().length - 1;
                hideChatWindow(swaped);
            } else {
                index = store.chatWindows.length;
            }
        } else {
            const newMessageChatWindowIndex = store.chatWindows.findIndex(
                (chatWindow) => !chatWindow.thread
            );
            index =
                newMessageChatWindowIndex !== -1
                    ? newMessageChatWindowIndex
                    : store.chatWindows.length;
        }
        store.chatWindows.splice(index, data.replaceNewMessageChatWindow ? 1 : 0, chatWindow);
        return store.chatWindows[index]; // return reactive version
    }
    assignDefined(chatWindow, data);
    return chatWindow;
}

export function makeChatWindowVisible(chatWindow) {
    const swaped = getVisibleChatWindows()[getVisibleChatWindows().length - 1];
    hideChatWindow(swaped);
    showChatWindow(chatWindow);
}

export function notifyChatWindowState(chatWindow) {
    if (ui.isSmall) {
        return;
    }
    if (chatWindow.thread?.model === "discuss.channel") {
        return orm.silent.call("discuss.channel", "channel_fold", [[chatWindow.thread.id]], {
            state: chatWindow.thread.state,
        });
    }
}

export const openChatWindow = makeFnPatchable(function (thread, replaceNewMessageChatWindow) {
    const chatWindow = insertChatWindow({
        folded: false,
        thread,
        replaceNewMessageChatWindow,
    });
    chatWindow.autofocus++;
    if (thread) {
        thread.state = "open";
    }
    return chatWindow;
});

export function openNewMessage() {
    if (store.chatWindows.some(({ thread }) => !thread)) {
        // New message chat window is already opened.
        return;
    }
    insertChatWindow();
}

export const showChatWindow = makeFnPatchable(function (chatWindow) {
    chatWindow.hidden = false;
    chatWindow.folded = false;
    chatWindow.thread.state = "open";
});

export const toggleFoldChatWindow = makeFnPatchable(function (chatWindow) {
    chatWindow.folded = !chatWindow.folded;
    const thread = chatWindow.thread;
    if (thread) {
        thread.state = chatWindow.folded ? "folded" : "open";
    }
});

export class ChatWindowService {
    constructor(env, services) {
        this.setup(env, services);
    }

    setup(env, services) {
        this.env = env;
        store = services["mail.store"];
        orm = services.orm;
        ui = services.ui;
    }
}

export const chatWindowService = {
    dependencies: ["mail.store", "orm", "ui"],
    start(env, services) {
        return new ChatWindowService(env, services);
    },
};

registry.category("services").add("mail.chat_window", chatWindowService);
