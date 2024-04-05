import { ChatWindow } from "@mail/core/common/chat_window";

import { Component, useExternalListener, useState, onMounted, useRef, useEffect } from "@odoo/owl";

import { browser } from "@web/core/browser/browser";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { localization } from "@web/core/l10n/localization";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class ChatWindowContainer extends Component {
    static components = { ChatWindow, Dropdown };
    static props = [];
    static template = "mail.ChatWindowContainer";

    setup() {
        super.setup();
        this.store = useState(useService("mail.store"));
        this.ui = useState(useService("ui"));
        this.hiddenMenuRef = useRef("hiddenMenu");
        useEffect(
            () => this.setHiddenMenuOffset(),
            () => [this.store.hiddenChatWindows]
        );
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
            this.store.CHAT_WINDOW_END_GAP_WIDTH +
            this.store.maxVisibleChatWindows *
                (this.store.CHAT_WINDOW_WIDTH + this.store.CHAT_WINDOW_END_GAP_WIDTH);
        const oppositeFrom = offsetFrom === "right" ? "left" : "right";
        this.hiddenMenuRef.el.style = `${offsetFrom}: ${visibleOffset}px; ${oppositeFrom}: auto`;
    }

    onResize() {
        while (this.store.visibleChatWindows.length > this.store.maxVisibleChatWindows) {
            this.store.visibleChatWindows.at(-1).hide();
        }
        while (
            this.store.visibleChatWindows.length < this.store.maxVisibleChatWindows &&
            this.store.hiddenChatWindows.length > 0
        ) {
            this.store.hiddenChatWindows[0].show();
        }
        this.setHiddenMenuOffset();
    }

    get unread() {
        let unreadCounter = 0;
        for (const chatWindow of this.store.hiddenChatWindows) {
            unreadCounter += chatWindow.thread.message_unread_counter;
        }
        return unreadCounter;
    }
}

registry
    .category("main_components")
    .add("mail.ChatWindowContainer", { Component: ChatWindowContainer });
