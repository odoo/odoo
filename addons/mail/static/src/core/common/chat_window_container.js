/* @odoo-module */

import { ChatWindow } from "@mail/core/common/chat_window";
import {
    CHAT_WINDOW_END_GAP_WIDTH,
    CHAT_WINDOW_INBETWEEN_WIDTH,
    CHAT_WINDOW_WIDTH,
    getHiddenChatWindows,
    getMaxVisibleChatWindows,
    getVisibleChatWindows,
    hideChatWindow,
    showChatWindow,
} from "@mail/core/common/chat_window_service";
import { useMessaging, useStore } from "@mail/core/common/messaging_hook";

import {
    Component,
    onWillStart,
    useExternalListener,
    useState,
    onMounted,
    useRef,
    useEffect,
} from "@odoo/owl";

import { browser } from "@web/core/browser/browser";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { localization } from "@web/core/l10n/localization";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class ChatWindowContainer extends Component {
    static components = { ChatWindow, Dropdown };
    static props = [];
    static template = "mail.ChatWindowContainer";

    get CHAT_WINDOW_END_GAP_WIDTH() {
        return CHAT_WINDOW_END_GAP_WIDTH;
    }

    get CHAT_WINDOW_INBETWEEN_WIDTH() {
        return CHAT_WINDOW_INBETWEEN_WIDTH;
    }

    get CHAT_WINDOW_WIDTH() {
        return CHAT_WINDOW_WIDTH;
    }

    setup() {
        this.messaging = useMessaging();
        this.store = useStore();
        this.chatWindowService = useState(useService("mail.chat_window"));
        this.ui = useState(useService("ui"));
        this.hiddenMenuRef = useRef("hiddenMenu");
        this.getHiddenChatWindows = getHiddenChatWindows;
        this.getVisibleChatWindows = getVisibleChatWindows;
        useEffect(
            () => this.setHiddenMenuOffset(),
            () => [getHiddenChatWindows()]
        );
        onWillStart(() => this.store.messagingReadyProm);
        onMounted(() => this.setHiddenMenuOffset());

        this.onResize();
        useExternalListener(browser, "resize", this.onResize);
    }

    setHiddenMenuOffset() {
        if (!this.hiddenMenuRef.el) {
            return;
        }
        const textDirection = localization.direction;
        const offsetFrom = textDirection === "rtl" ? "left" : "right";
        const visibleOffset =
            CHAT_WINDOW_END_GAP_WIDTH +
            getMaxVisibleChatWindows() * (CHAT_WINDOW_WIDTH + CHAT_WINDOW_END_GAP_WIDTH);
        const oppositeFrom = offsetFrom === "right" ? "left" : "right";
        this.hiddenMenuRef.el.style = `${offsetFrom}: ${visibleOffset}px; ${oppositeFrom}: auto`;
    }

    onResize() {
        while (getVisibleChatWindows().length > getMaxVisibleChatWindows()) {
            hideChatWindow(getVisibleChatWindows()[getVisibleChatWindows().length - 1]);
        }
        while (
            getVisibleChatWindows().length < getMaxVisibleChatWindows() &&
            getHiddenChatWindows().length > 0
        ) {
            showChatWindow(getHiddenChatWindows()[0]);
        }
        this.setHiddenMenuOffset();
    }

    get unread() {
        let unreadCounter = 0;
        for (const chatWindow of getHiddenChatWindows()) {
            unreadCounter += chatWindow.thread.message_unread_counter;
        }
        return unreadCounter;
    }
}

registry
    .category("main_components")
    .add("mail.ChatWindowContainer", { Component: ChatWindowContainer });
