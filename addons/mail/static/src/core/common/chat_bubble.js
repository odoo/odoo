import { ImStatus } from "@mail/core/common/im_status";

import { Component, useEffect, useRef, useState } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";
import { useHover, useMovable } from "@mail/utils/common/hooks";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { CountryFlag } from "@mail/core/common/country_flag";

/**
 * @typedef {Object} Props
 * @extends {Component<Props, Env>}
 */
export class ChatBubble extends Component {
    static components = { CountryFlag, ImStatus, Dropdown };
    static props = ["chatWindow"];
    static template = "mail.ChatBubble";

    setup() {
        super.setup();
        this.store = useState(useService("mail.store"));
        this.wasHover = false;
        this.hover = useHover(["root", "preview*"], {
            onHover: () => (this.preview.isOpen = true),
            onHovering: [100, () => (this.state.showClose = true)],
            onAway: () => {
                this.state.showClose = false;
                this.preview.isOpen = false;
            },
        });
        this.preview = useDropdownState();
        this.rootRef = useRef("root");
        this.state = useState({ bouncing: false, showClose: true });
        useEffect(
            (importantCounter) => {
                this.state.bouncing = Boolean(importantCounter);
            },
            () => [this.thread?.importantCounter]
        );
        if (this.env.embedLivechat) {
            this.position = useState({ left: "auto", top: "auto" });
            useMovable({
                cursor: "grabbing",
                ref: this.rootRef,
                elements: ".o-mail-ChatBubble",
                onDrop: ({ top, left }) =>
                    Object.assign(this.position, { left: `${left}px`, top: `${top}px` }),
            });
        }
    }

    /** @returns {import("models").Thread} */
    get thread() {
        return this.props.chatWindow.thread;
    }

    get previewContent() {
        const lastMessage = this.thread?.newestPersistentNotEmptyOfAllMessage;
        if (!lastMessage) {
            return false;
        }
        return lastMessage.inlineBody;
    }
}
