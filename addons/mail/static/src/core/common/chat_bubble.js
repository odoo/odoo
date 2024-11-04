import { ImStatus } from "@mail/core/common/im_status";

import { Component, useEffect, useRef, useState } from "@odoo/owl";

import { useChildRef, useService } from "@web/core/utils/hooks";
import { useHover, useMovable } from "@mail/utils/common/hooks";
import { usePopover } from "@web/core/popover/popover_hook";

class ChatBubblePreview extends Component {
    static props = ["chatWindow", "close"];
    static template = "mail.ChatBubble.preview";

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

/**
 * @typedef {Object} Props
 * @extends {Component<Props, Env>}
 */
export class ChatBubble extends Component {
    static components = { ImStatus };
    static props = ["chatWindow"];
    static template = "mail.ChatBubble";

    setup() {
        super.setup();
        this.store = useState(useService("mail.store"));
        const popoverRef = useChildRef();
        this.popover = usePopover(ChatBubblePreview, {
            animation: false,
            position: "left-middle",
            popoverClass: "bg-view border-0 p-0 overflow-visible rounded-3",
            ref: popoverRef,
        });
        this.env.bus.addEventListener("chat-bubble:preview-will-open", ({ detail }) => {
            if (detail === this) {
                return;
            }
            this.popover.close();
        });
        this.wasHover = false;
        this.hover = useHover(["root", popoverRef], () => {
            if (this.hover.isHover && !this.wasHover) {
                clearTimeout(this.showCloseTimeout);
                this.showCloseTimeout = setTimeout(() => (this.state.showClose = true), 100);
                if (!this.env.embedLivechat) {
                    this.env.bus.trigger("chat-bubble:preview-will-open", this);
                    this.popover.open(this.rootRef.el.querySelector(".o-mail-ChatHub-bubbleBtn"), {
                        chatWindow: this.props.chatWindow,
                    });
                }
            } else if (!this.hover.isHover) {
                clearTimeout(this.showCloseTimeout);
                this.state.showClose = false;
                this.popover.close();
            }
            this.wasHover = this.hover.isHover;
        });
        this.rootRef = useRef("root");
        this.state = useState({ bouncing: false, showClose: true });
        useEffect(
            () => {
                this.state.bouncing = this.thread.importantCounter ? true : this.state.bouncing;
            },
            () => [this.thread.importantCounter]
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
}
