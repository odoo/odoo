/* @odoo-module */

import { ChatWindow } from "@mail/new/web/chat_window/chat_window";
import {
    CHAT_WINDOW_END_GAP_WIDTH,
    CHAT_WINDOW_INBETWEEN_WIDTH,
    CHAT_WINDOW_WIDTH,
} from "@mail/new/web/chat_window/chat_window_service";
import { useMessaging, useStore } from "@mail/new/core/messaging_hook";

import { Component, onWillStart, useExternalListener, useState } from "@odoo/owl";

import { browser } from "@web/core/browser/browser";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class ChatWindowContainer extends Component {
    static components = { ChatWindow, Dropdown };
    static props = [];
    static template = "mail.chat_window_container";

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
        onWillStart(() => this.messaging.isReady);

        this.onResize();
        useExternalListener(browser, "resize", this.onResize);
    }

    onResize() {
        while (this.chatWindowService.visible.length > this.chatWindowService.maxVisible) {
            this.chatWindowService.hide(
                this.chatWindowService.visible[this.chatWindowService.visible.length - 1]
            );
        }
        while (
            this.chatWindowService.visible.length < this.chatWindowService.maxVisible &&
            this.chatWindowService.hidden.length > 0
        ) {
            this.chatWindowService.show(this.chatWindowService.hidden[0]);
        }
    }

    get unread() {
        let unreadCounter = 0;
        for (const chatWindow of this.chatWindowService.hidden) {
            unreadCounter += chatWindow.thread.message_unread_counter;
        }
        return unreadCounter;
    }
}

registry
    .category("main_components")
    .add("mail.ChatWindowContainer", { Component: ChatWindowContainer });
