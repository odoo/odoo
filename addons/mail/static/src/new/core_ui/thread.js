/* @odoo-module */

import { Component, onMounted, onWillStart, onWillUpdateProps, useRef, useState } from "@odoo/owl";
import { useMessaging, useStore } from "../core/messaging_hook";
import {
    useAutoScroll,
    useScrollPosition,
    useScrollSnapshot,
    useVisible,
} from "@mail/new/utils/hooks";
import { Message } from "./message";

import { Transition } from "@web/core/transition";
import { useService } from "@web/core/utils/hooks";

/**
 * @typedef {Object} Props
 * @property {boolean} [isInChatWindow=false]
 * @property {import("@mail/new/utils/hooks").MessageEdition} [messageEdition]
 * @property {import("@mail/new/utils/hooks").MessageHighlight} [messageHighlight]
 * @property {import("@mail/new/utils/hooks").MessageToReplyTo} [messageToReplyTo]
 * @property {"asc"|"desc"} [order="asc"]
 * @property {import("@mail/new/core/thread_model").Thread} thread
 * @extends {Component<Props, Env>}
 */
export class Thread extends Component {
    static components = { Message, Transition };
    static props = [
        "isInChatWindow?",
        "thread",
        "messageEdition?",
        "messageHighlight?",
        "messageToReplyTo?",
        "order?",
    ];
    static defaultProps = {
        isInChatWindow: false,
        order: "asc", // 'asc' or 'desc'
    };
    static template = "mail.thread";

    setup() {
        this.messaging = useMessaging();
        this.store = useStore();
        this.state = useState({ isReplyingTo: false });
        /** @type {import("@mail/new/core/thread_service").ThreadService} */
        this.threadService = useState(useService("mail.thread"));
        if (!this.env.inChatter) {
            useAutoScroll("messages", () => {
                if (
                    this.props.messageHighlight &&
                    this.props.messageHighlight.highlightedMessageId
                ) {
                    return false;
                }
                if (this.props.thread.scrollPosition.isSaved) {
                    return false;
                }
                return true;
            });
        }
        this.messagesRef = useRef("messages");
        this.loadMoreState = useVisible("load-more", () => {
            if (this.loadMoreState.isVisible) {
                this.threadService.fetchMoreMessages(this.props.thread);
            }
        });
        this.oldestNonTransientMessageId = null;
        this.scrollPosition = useScrollPosition(
            "messages",
            this.props.thread.scrollPosition,
            "bottom"
        );
        useScrollSnapshot("messages", {
            onWillPatch: () => {
                return {
                    hasMoreMsgsAbove:
                        this.props.thread.oldestNonTransientMessage?.id !==
                            this.oldestNonTransientMessage && this.props.order === "asc",
                };
            },
            onPatched: ({ hasMoreMsgsAbove, scrollTop, scrollHeight }) => {
                const el = this.messagesRef.el;
                if (hasMoreMsgsAbove) {
                    el.scrollTop = scrollTop + el.scrollHeight - scrollHeight;
                }
                this.oldestNonTransientMessage = this.props.thread.oldestNonTransientMessage?.id;
            },
        });
        onMounted(() => {
            this.oldestNonTransientMessage = this.props.thread.oldestNonTransientMessage?.id;
            this.scrollPosition.restore();
        });
        onWillStart(() => {
            this.threadService.fetchNewMessages(this.props.thread);
        });
        onWillUpdateProps((nextProps) => {
            this.threadService.fetchNewMessages(nextProps.thread);
        });
    }

    onClickLoadMore() {
        this.threadService.fetchMoreMessages(this.props.thread);
    }

    isSquashed(msg, prevMsg) {
        if (this.props.thread.model === "mail.box") {
            return false;
        }
        if (!prevMsg || prevMsg.type === "notification" || prevMsg.isEmpty || this.env.inChatter) {
            return false;
        }

        if (msg.author !== prevMsg.author) {
            return false;
        }
        if (msg.resModel !== prevMsg.resModel || msg.resId !== prevMsg.resId) {
            return false;
        }
        if (msg.parentMessage) {
            return false;
        }
        return msg.datetime.ts - prevMsg.datetime.ts < 60 * 1000;
    }
}
