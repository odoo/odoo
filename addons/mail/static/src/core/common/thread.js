/* @odoo-module */

import { DateSection } from "@mail/core/common/date_section";
import { Message } from "@mail/core/common/message";
import {
    useAutoScroll,
    useScrollPosition,
    useScrollSnapshot,
    useVisible,
} from "@mail/utils/common/hooks";

import { Component, onMounted, onWillUpdateProps, useEffect, useRef, useState } from "@odoo/owl";

import { Transition } from "@web/core/transition";
import { useBus, useService } from "@web/core/utils/hooks";
import { escape } from "@web/core/utils/strings";

export const PRESENT_THRESHOLD = 2500;

/**
 * @typedef {Object} Props
 * @property {boolean} [isInChatWindow=false]
 * @property {number} [jumpPresent=0]
 * @property {import("@mail/utils/common/hooks").MessageEdition} [messageEdition]
 * @property {import("@mail/utils/common/hooks").MessageToReplyTo} [messageToReplyTo]
 * @property {"asc"|"desc"} [order="asc"]
 * @property {import("models").Thread} thread
 * @property {string} [searchTerm]
 * @property {import("@web/core/utils/hooks").Ref} [scrollRef]
 * @extends {Component<Props, Env>}
 */
export class Thread extends Component {
    static components = { Message, Transition, DateSection };
    static props = [
        "showDates?",
        "isInChatWindow?",
        "jumpPresent?",
        "thread",
        "messageEdition?",
        "messageToReplyTo?",
        "order?",
        "scrollRef?",
        "showEmptyMessage?",
        "showJumpPresent?",
        "messageActions?",
    ];
    static defaultProps = {
        isInChatWindow: false,
        jumpPresent: 0,
        order: "asc",
        showDates: true,
        showEmptyMessage: true,
        showJumpPresent: true,
        messageActions: true
    };
    static template = "mail.Thread";

    setup() {
        this.escape = escape;
        this.store = useState(useService("mail.store"));
        this.state = useState({
            isReplyingTo: false,
            mountedAndLoaded: false,
            showJumpPresent: false,
        });
        this.threadService = useState(useService("mail.thread"));
        useAutoScroll("messages", () => {
            if (this.env.messageHighlight?.highlightedMessageId) {
                return false;
            }
            if (this.props.thread.scrollPosition.isSaved) {
                return false;
            }
            return true;
        });
        /** @type {ReturnType<import('@mail/utils/common/hooks').useMessageHighlight>|null} */
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
        useScrollSnapshot(this.env.inChatter ? this.props.scrollRef : this.messagesRef, {
            onWillPatch: () => {
                return {
                    hasMoreMsgsAbove:
                        this.props.thread.oldestPersistentMessage?.id <
                        this.oldestPersistentMessage,
                    hasMoreMsgBelow:
                        this.props.thread.loadNewer &&
                        this.props.thread.newestPersistentMessage?.id >
                            this.newestPersistentMessage,
                };
            },
            onPatched: ({ hasMoreMsgsAbove, hasMoreMsgBelow, scrollTop, scrollHeight }) => {
                const el = this.messagesRef.el;
                if (!this.isJumpingRecent) {
                    if (hasMoreMsgsAbove) {
                        el.scrollTop = this.env.inChatter
                            ? scrollTop
                            : scrollTop + el.scrollHeight - scrollHeight;
                    } else if (hasMoreMsgBelow) {
                        el.scrollTop = this.env.inChatter
                            ? scrollTop + el.scrollHeight - scrollHeight
                            : scrollTop;
                    }
                }
                this.oldestPersistentMessage = this.props.thread.oldestPersistentMessage?.id;
                this.newestPersistentMessage = this.props.thread.newestPersistentMessage?.id;
            },
        });
        useEffect(
            () => this.updateShowJumpPresent(),
            () => [this.props.thread.loadNewer]
        );
        useEffect(
            () => {
                if (
                    this.props.jumpPresent !== this.lastJumpPresent &&
                    this.props.thread.loadNewer
                ) {
                    this.jumpToPresent("instant");
                    this.lastJumpPresent = this.props.jumpPresent;
                }
            },
            () => [this.props.jumpPresent]
        );
        useEffect(
            () => {
                if (!this.state.mountedAndLoaded) {
                    return;
                }
                this.oldestPersistentMessage = this.props.thread.oldestPersistentMessage?.id;
                if (!this.env.inChatter) {
                    this.scrollPosition.restore();
                    this.updateShowJumpPresent();
                }
            },
            () => [this.state.mountedAndLoaded]
        );
        onMounted(async () => {
            this.lastJumpPresent = this.props.jumpPresent;
            await this.threadService.fetchNewMessages(this.props.thread);
            this.state.mountedAndLoaded = true;
        });
        useBus(this.env.bus, "MAIL:RELOAD-THREAD", ({ detail }) => {
            const { model, id } = this.props.thread;
            if (detail.model === model && detail.id === id) {
                this.threadService.fetchNewMessages(this.props.thread);
            }
        });
        onWillUpdateProps((nextProps) => {
            if (nextProps.thread.notEq(this.props.thread)) {
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
            await this.env.messageHighlight?.highlightMessage(
                this.store.Message.insert({
                    id: Number(oeId),
                    res_id: this.props.thread.id,
                    model: this.props.thread.model,
                }),
                this.props.thread
            );
        }
    }

    isSquashed(msg, prevMsg) {
        if (this.props.thread.model === "mail.box") {
            return false;
        }
        if (!prevMsg || prevMsg.type === "notification" || prevMsg.isEmpty || this.env.inChatter) {
            return false;
        }

        if (!msg.author?.eq(prevMsg.author)) {
            return false;
        }
        if (msg.model !== prevMsg.model || msg.res_id !== prevMsg.res_id) {
            return false;
        }
        if (msg.parentMessage) {
            return false;
        }
        return msg.datetime.ts - prevMsg.datetime.ts < 60 * 1000;
    }
}
