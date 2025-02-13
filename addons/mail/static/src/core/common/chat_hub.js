import { ChatWindow } from "@mail/core/common/chat_window";
import { useHover, useMovable } from "@mail/utils/common/hooks";
import { Component, useEffect, useExternalListener, useRef, useState } from "@odoo/owl";

import { browser } from "@web/core/browser/browser";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { ChatBubble } from "./chat_bubble";
import { isMobileOS } from "@web/core/browser/feature_detection";

export class ChatHub extends Component {
    static components = { ChatBubble, ChatWindow, Dropdown };
    static props = [];
    static template = "mail.ChatHub";

    get chatHub() {
        return this.store.chatHub;
    }

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.ui = useService("ui");
        this.busMonitoring = useService("bus.monitoring_service");
        this.bubblesHover = useHover("bubbles");
        this.moreHover = useHover(["more-button", "more-menu*"], {
            onHover: () => (this.more.isOpen = true),
            onAway: () => (this.more.isOpen = false),
        });
        this.options = useDropdownState();
        this.more = useDropdownState();
        this.ref = useRef("bubbles");
        this.position = useState({
            dragged: false,
            isDragging: false,
            top: "unset",
            left: "unset",
            bottom: `${this.chatHub.BUBBLE_OUTER}px;`,
            right: `${this.chatHub.BUBBLE_OUTER + this.chatHub.BUBBLE_START}px;`,
        });
        this.onResize();
        useExternalListener(browser, "resize", this.onResize);
        useEffect(() => {
            if (this.chatHub.folded.length && this.store.channels?.status === "not_fetched") {
                this.store.channels.fetch();
            }
        });
        useMovable({
            cursor: "grabbing",
            ref: this.ref,
            elements: ".o-mail-ChatHub-bubbles",
            onDragStart: () => {
                this.more.close();
                this.options.close();
                this.position.isDragging = true;
                this.position.dragged = true;
            },
            onDragEnd: () => (this.position.isDragging = false),
            onDrop: this.onDrop.bind(this),
        });
    }

    get isMobileOS() {
        return isMobileOS();
    }

    onDrop({ top, left }) {
        this.position.bottom = "unset";
        this.position.right = "unset";
        this.position.top = `${top}px`;
        this.position.left = `${left}px`;
    }

    onResize() {
        this.chatHub.onRecompute();
    }

    resetPosition() {
        this.position.top = "unset";
        this.position.left = "unset";
        this.position.bottom = `${this.chatHub.BUBBLE_OUTER}px;`;
        this.position.right = `${this.chatHub.BUBBLE_OUTER + this.chatHub.BUBBLE_START}px;`;
        this.position.dragged = false;
        this.options.close();
    }

    get compactCounter() {
        let counter = 0;
        const cws = this.chatHub.opened.concat(this.chatHub.folded);
        for (const chatWindow of cws) {
            counter += chatWindow.thread.importantCounter > 0 ? 1 : 0;
        }
        return counter;
    }

    get hiddenCounter() {
        let counter = 0;
        for (const chatWindow of this.chatHub.folded.slice(this.chatHub.maxFolded)) {
            counter += chatWindow.thread.importantCounter > 0 ? 1 : 0;
        }
        return counter;
    }

    get displayConversations() {
        return this.chatHub.opened.length + this.chatHub.folded.length > 0 && !this.chatHub.compact;
    }

    get isShown() {
        return true;
    }

    expand() {
        this.chatHub.compact = false;
        this.more.isOpen = this.chatHub.folded.length > this.chatHub.maxFolded;
    }
}

registry.category("main_components").add("mail.ChatHub", { Component: ChatHub });
