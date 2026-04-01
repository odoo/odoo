import { ImStatus } from "@mail/core/common/im_status";

import { Component, useEffect, useRef, useState, useSubEnv } from "@odoo/owl";

import { useChildRef, useService } from "@web/core/utils/hooks";
import { useHover } from "@mail/utils/common/hooks";
import { usePopover } from "@web/core/popover/popover_hook";
import { CountryFlag } from "@mail/core/common/country_flag";
import { isMobileOS } from "@web/core/browser/feature_detection";

class ChatBubblePreview extends Component {
    static props = ["chatWindow", "close"];
    static template = "mail.ChatBubblePreview";

    /** @returns {import("models").Thread} */
    get thread() {
        return this.props.chatWindow.thread;
    }

    get previewText() {
        const lastMessage = this.thread?.newestPersistentOfAllMessage;
        if (!lastMessage) {
            return false;
        }
        return lastMessage.previewText;
    }
}

/**
 * @typedef {Object} Props
 * @extends {Component<Props, Env>}
 */
export class ChatBubble extends Component {
    static components = { CountryFlag, ImStatus };
    static props = ["chatWindow"];
    static template = "mail.ChatBubble";

    setup() {
        super.setup();
        this.store = useService("mail.store");
        const popoverRef = useChildRef();
        this.isMobileOS = isMobileOS();
        this.popover = usePopover(ChatBubblePreview, {
            animation: false,
            position: "left-middle",
            popoverClass:
                "dropdown-menu bg-view border-0 p-0 overflow-visible o-rounded-bubble mx-1",
            ref: popoverRef,
        });
        this.env.bus.addEventListener("ChatBubble:preview-will-open", ({ detail }) => {
            if (detail === this) {
                return;
            }
            this.popover.close();
        });
        this.hover = useHover(["root", popoverRef], {
            onHover: () => {
                this.env.bus.trigger("ChatBubble:preview-will-open", this);
                this.popover.open(this.rootRef.el, { chatWindow: this.props.chatWindow });
            },
            onAway: () => this.popover.close(),
        });
        this.rootRef = useRef("root");
        this.state = useState({ bouncing: false });
        useEffect(
            (importantCounter) => {
                this.state.bouncing = Boolean(importantCounter);
            },
            () => [this.thread?.importantCounter]
        );
        useSubEnv({ inChatBubble: true });
    }

    /** @returns {import("models").Thread} */
    get thread() {
        return this.props.chatWindow.thread;
    }

    get showImStatus() {
        return (
            this.thread?.correspondent?.im_status &&
            this.thread.correspondent.im_status !== "offline"
        );
    }
}
