/* @odoo-module */

import { Message } from "@mail/core/common/message";
import { useMessaging, useStore } from "@mail/core/common/messaging_hook";
import {
    useAutoScroll,
    useScrollPosition,
    useScrollSnapshot,
    useVisible,
} from "@mail/utils/common/hooks";

import {
    Component,
    onMounted,
    onWillStart,
    onWillUpdateProps,
    useEffect,
    useRef,
    useState,
} from "@odoo/owl";

import { Transition } from "@web/core/transition";
import { useService } from "@web/core/utils/hooks";
import { escape } from "@web/core/utils/strings";

export const PRESENT_THRESHOLD = 2500;

/**
 * @typedef {Object} Props
 * @property {boolean} [isInChatWindow=false]
 * @property {number} [jumpPresent=0]
 * @property {import("@mail/utils/common/hooks").MessageEdition} [messageEdition]
 * @property {import("@mail/utils/common/hooks").MessageToReplyTo} [messageToReplyTo]
 * @property {"asc"|"desc"} [order="asc"]
 * @property {import("@mail/core/common/thread_model").Thread} thread
 * @extends {Component<Props, Env>}
 */
export class Thread extends Component {
    static components = { Message, Transition };
    static props = [
        "isInChatWindow?",
        "hasScrollAdjust?",
        "jumpPresent?",
        "thread",
        "messageEdition?",
        "messageToReplyTo?",
        "order?",
    ];
    static defaultProps = {
        isInChatWindow: false,
        hasScrollAdjust: true,
        jumpPresent: 0,
        order: "asc", // 'asc' or 'desc'
    };
    static template = "mail.Thread";

    setup() {
        this.escape = escape;
        this.messaging = useMessaging();
        this.store = useStore();
        this.state = useState({ isReplyingTo: false, showJumpPresent: false });
        /** @type {import("@mail/core/common/thread_service").ThreadService} */
        this.threadService = useState(useService("mail.thread"));
        if (!this.env.inChatter || !this.props.hasScrollAdjust) {
            useAutoScroll("messages", () => {
                if (this.env.messageHighlight?.highlightedMessageId) {
                    return false;
                }
                if (this.props.thread.scrollPosition.isSaved) {
                    return false;
                }
                return true;
            });
        }
        this.messageHighlight = this.env.messageHighlight
            ? useState(this.env.messageHighlight)
            : null;
        this.present = useRef("load-newer");
        this.messagesRef = useRef("messages");
        this.loadOlderState = useVisible("load-older", () => {
            if (this.loadOlderState.isVisible && !this.isJumpingRecent) {
                this.threadService.fetchMoreMessages(this.props.thread);
            }
        });
        this.loadNewerState = useVisible("load-newer", () => {
            if (this.loadNewerState.isVisible && !this.isJumpingRecent) {
                this.threadService.fetchMoreMessages(this.props.thread, "newer");
            }
        });
        this.presentThresholdState = useVisible(
            "present-treshold",
            () => this.updateShowJumpPresent(),
            { init: true }
        );
        this.oldestPersistentMessageId = null;
        this.scrollPosition = useScrollPosition(
            "messages",
            this.props.thread.scrollPosition,
            "bottom"
        );
        if (!this.env.inChatter || !this.props.hasScrollAdjust) {
            useScrollSnapshot("messages", {
                onWillPatch: () => {
                    return {
                        hasMoreMsgsAbove:
                            this.props.thread.oldestPersistentMessage?.id <
                                this.oldestPersistentMessage && this.props.order === "asc",
                        hasMoreMsgBelow:
                            this.props.thread.loadNewer &&
                            this.props.thread.newestPersistentMessage?.id >
                                this.newestPersistentMessage &&
                            this.props.order === "asc",
                    };
                },
                onPatched: ({ hasMoreMsgsAbove, hasMoreMsgBelow, scrollTop, scrollHeight }) => {
                    const el = this.messagesRef.el;
                    if (!this.isJumpingRecent) {
                        if (hasMoreMsgsAbove) {
                            el.scrollTop = scrollTop + el.scrollHeight - scrollHeight;
                        } else if (hasMoreMsgBelow) {
                            el.scrollTop = scrollTop;
                        }
                    }
                    this.oldestPersistentMessage = this.props.thread.oldestPersistentMessage?.id;
                    this.newestPersistentMessage = this.props.thread.newestPersistentMessage?.id;
                },
            });
        }
        useEffect(
            () => this.updateShowJumpPresent(),
            () => [this.props.thread.loadNewer]
        );
        useEffect(
            () => {
                if (this.props.jumpPresent !== this.lastJumpPresent) {
                    this.jumpToPresent("instant");
                    this.lastJumpPresent = this.props.jumpPresent;
                }
            },
            () => [this.props.jumpPresent]
        );
        onMounted(() => {
            this.oldestPersistentMessage = this.props.thread.oldestPersistentMessage?.id;
            if (!this.env.inChatter || !this.props.hasScrollAdjust) {
                this.scrollPosition.restore();
                this.updateShowJumpPresent();
            }
        });
        onWillStart(() => {
            this.lastJumpPresent = this.props.jumpPresent;
            this.threadService.fetchNewMessages(this.props.thread);
        });
        onWillUpdateProps((nextProps) => {
            if (nextProps.thread !== this.props.thread) {
                this.lastJumpPresent = nextProps.jumpPresent;
            }
            this.threadService.fetchNewMessages(nextProps.thread);
        });
    }

    get PRESENT_THRESHOLD() {
        return this.state.showJumpPresent ? PRESENT_THRESHOLD - 200 : PRESENT_THRESHOLD;
    }

    updateShowJumpPresent() {
        this.state.showJumpPresent =
            this.props.thread.loadNewer || !this.presentThresholdState.isVisible;
    }

    onClickLoadOlder() {
        this.threadService.fetchMoreMessages(this.props.thread);
    }

    async jumpToPresent(behavior) {
        this.isJumpingRecent = true;
        await this.threadService.loadAround(this.props.thread);
        this.props.thread.loadNewer = false;
        this.present.el?.scrollIntoView({
            behavior: behavior ?? (this.props.order === "asc" ? "smooth" : "instant"), // FIXME somehow smooth not working in desc mode
            block: "center",
        });
        // Let smooth scroll a bit so load more is not visible
        // smooth scrolling starts after 1 animation frame, hence needs to wait 2 animation frames
        // for load more becoming not visible
        await new Promise((resolve) => setTimeout(() => requestAnimationFrame(resolve)));
        await new Promise((resolve) => setTimeout(() => requestAnimationFrame(resolve)));
        this.state.showJumpPresent = false;
        this.isJumpingRecent = false;
    }

    /**
     * @param {MouseEvent} ev
     */
    async onClickNotification(ev) {
        const { oeType, oeId } = ev.target.dataset;
        if (oeType === "highlight") {
            await this.env.messageHighlight?.highlightMessage(Number(oeId), this.props.thread);
        }
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
