// @ts-check
/** @odoo-module native */
import { CountryFlag } from "@mail/core/common/country_flag";
import { ImStatus } from "@mail/core/common/im_status";
import { baseImStatus } from "@mail/core/common/presence_status";
import { useHover } from "@mail/utils/common/hooks";
import { Component, useEffect, useRef, useState, useSubEnv } from "@odoo/owl";
import { isMobileOS } from "@web/core/browser/feature_detection";
import { makeLogger } from "@web/core/debug/debug_logger";
import { useBus, useChildRef, useService } from "@web/core/utils/hooks";
import { usePopover } from "@web/ui/popover";

const log = makeLogger("mail.chat_hub");
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
 * @extends {Component<Props, import("@web/env").OdooEnv>}
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
            class: "dropdown-menu bg-view border-0 p-0 overflow-visible o-rounded-bubble mx-1",
            ref: popoverRef,
        });
        useBus(
            this.env.bus,
            "ChatBubble:preview-will-open",
            /** @param {CustomEvent<ChatBubble>} ev */
            ({ detail }) => {
                if (detail === this) {
                    return;
                }
                this.popover.close();
            },
        );
        this.hover = useHover(["root", popoverRef], {
            onHover: () => {
                log.logic("preview open", () => ({ thread: this.thread?.localId }));
                this.env.bus.trigger("ChatBubble:preview-will-open", this);
                this.popover.open(this.rootRef.el, {
                    chatWindow: this.props.chatWindow,
                });
            },
            onAway: () => this.popover.close(),
        });
        this.rootRef = useRef("root");
        this.state = useState({ bouncing: false });
        useEffect(
            /** @param {number|undefined} importantCounter */
            (importantCounter) => {
                this.state.bouncing = Boolean(importantCounter);
            },
            () => [this.thread?.importantCounter],
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
            baseImStatus(this.thread.correspondent.im_status) !== "offline"
        );
    }
}
