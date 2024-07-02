import { ChatWindow } from "@mail/core/common/chat_window";
import { useHover, useMovable } from "@mail/utils/common/hooks";
import { Component, useEffect, useExternalListener, useRef, useState } from "@odoo/owl";

import { browser } from "@web/core/browser/browser";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { ChatBubble } from "./chat_bubble";

export class ChatHub extends Component {
    static components = { ChatBubble, ChatWindow, Dropdown };
    static props = [];
    static template = "mail.ChatHub";

    get chatHub() {
        return this.store.chatHub;
    }

    setup() {
        super.setup();
        this.store = useState(useService("mail.store"));
        this.ui = useState(useService("ui"));
        this.bubblesHover = useHover("bubbles");
        this.moreHover = useHover(["more-button", "more-menu*"], () => {
            this.more.isOpen = this.moreHover.isHover;
        });
        this.options = useDropdownState();
        this.more = useDropdownState();
        this.compactRef = useRef("compact");
        this.compactPosition = useState({ left: "auto", top: "auto" });
        this.onResize();
        useExternalListener(browser, "resize", this.onResize);
        useEffect(() => {
            if (
                this.chatHub.actuallyFolded.length &&
                this.store.channels?.status === "not_fetched"
            ) {
                this.store.channels.fetch();
            }
        });
        useMovable({
            cursor: "grabbing",
            ref: this.compactRef,
            elements: ".o-mail-ChatHub-compact",
            onDrop: ({ top, left }) =>
                Object.assign(this.compactPosition, { left: `${left}px`, top: `${top}px` }),
        });
    }

    onResize() {
        this.chatHub.onRecompute();
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
        for (const chatWindow of this.chatHub.actuallyHidden) {
            counter += chatWindow.thread.importantCounter > 0 ? 1 : 0;
        }
        return counter;
    }

    expand() {
        this.chatHub.compact = false;
        Object.assign(this.compactPosition, { left: "auto", top: "auto" });
        this.more.isOpen = this.chatHub.actuallyHidden.length !== 0;
    }
}

registry.category("main_components").add("mail.ChatHub", { Component: ChatHub });
