// @ts-check
/** @odoo-module native */
import { DateSection } from "@mail/core/common/date_section";
import { Message } from "@mail/core/common/message";
import { useThreadScroll } from "@mail/core/common/thread_scroll_hook";
import { useVisible } from "@mail/utils/common/hooks";
import { markThreadAsReadIfAtBottom } from "@mail/utils/common/thread_read";
import {
    Component,
    markRaw,
    onMounted,
    onPatched,
    onWillUnmount,
    onWillUpdateProps,
    reactive,
    toRaw,
    useChildSubEnv,
    useEffect,
    useRef,
    useState,
} from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { makeLogger } from "@web/core/debug/debug_logger";
import { useLifecycleLog } from "@web/core/debug/logger_hooks";
import { Transition } from "@web/core/transition";
import { measure, mutate } from "@web/core/utils/dom/layout_batch";
import { useBus, useRefListener, useService } from "@web/core/utils/hooks";
import { useThrottleForAnimation } from "@web/core/utils/timing";

import { NotificationMessage } from "./notification_message.js";

export const PRESENT_VIEWPORT_THRESHOLD = 1;
const log = makeLogger("mail.thread.ui");

/**
 * @typedef {Object} Props
 * @property {number} [autofocus]
 * @property {boolean} [isInChatWindow=false]
 * @property {number} [jumpPresent=0]
 * @property {number} [jumpToNewMessage=0]
 * @property {"asc"|"desc"} [order="asc"]
 * @property {import("models").Thread} thread
 * @property {import("@web/core/utils/hooks").Ref} [scrollRef]
 * @property {boolean} [showDates=true]
 * @property {boolean} [showEmptyMessage=true]
 * @property {boolean} [showJumpPresent=true]
 * @property {boolean} [messageActions=true]
 * @extends {Component<Props, import("@web/env").OdooEnv>}
 */
export class Thread extends Component {
    static components = { Message, NotificationMessage, Transition, DateSection };
    static props = [
        "autofocus?",
        "showDates?",
        "isInChatWindow?",
        "jumpPresent?",
        "jumpToNewMessage?",
        "thread",
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
        messageActions: true,
    };
    static template = "mail.Thread";

    _setupServicesAndRefs() {
        this.onScroll = useThrottleForAnimation(this.onScroll);
        this.registerMessageRef = this.registerMessageRef.bind(this);
        this.store = useService("mail.store");
        this.ui = useService("ui");
        this.state = useState({
            isReplyingTo: false,
            mountedAndLoaded: false,
            resetCount: 0,
            showJumpPresent: false,
            scrollTop: null,
        });
        this.lastJumpPresent = this.props.jumpPresent;
        /** @type {ReturnType<import('@mail/utils/common/hooks').useMessageScrolling>|null} */
        this.messageHighlight = this.env.messageHighlight
            ? useState(this.env.messageHighlight)
            : null;
        this.scrollingToHighlight = false;
        /** @type {HTMLElement|null|undefined} */
        this._viewportEl = undefined;
        // a patch of this component can grow the scrollable past the window and Owl
        // may render again in the same flush, before the ResizeObserver below can
        // see the growth: the cache does not survive a patch
        onPatched(() => this.computeJumpPresentPosition());
        this.refByMessageId = reactive(new Map(), () => {
            this.scrollToHighlighted();
        });
        useEffect(
            () => {
                this.scrollToHighlighted();
            },
            () => [this.messageHighlight?.highlightedMessageId],
        );
        this.jumpPresentRef = useRef("jump-present");
        this.presentThresholdRef = useRef("present-treshold");
        this.root = useRef("messages");
        this.visibleState = useVisible("messages", () => {
            this.updateShowJumpPresent();
        });
        this.scrollableRef = this.props.scrollRef ?? this.root;
        useRefListener(
            this.scrollableRef,
            "scrollend",
            () => (this.state.scrollTop = this.scrollableRef.el.scrollTop),
        );
        this.presentThresholdState = useVisible("present-treshold", () =>
            this.updateShowJumpPresent(),
        );
    }
    _setupScrollTracking() {
        this.threadScroll = useThreadScroll({
            scrollableRef: this.scrollableRef,
            getThread: () => this.props.thread,
            getOrder: () => this.props.order,
            getMountedAndLoaded: () => this.state.mountedAndLoaded,
            getMessageHighlight: () => this.messageHighlight,
            getHighlightedMessageId: () =>
                this.env.messageHighlight?.highlightedMessageId,
            /** @param {import("models").Thread} thread */
            applyScrollContextually: (thread) => this.applyScrollContextually(thread),
            onReset: () => {
                this.state.mountedAndLoaded = false;
                if (this.props.thread.isLoaded) {
                    this.state.resetCount++;
                }
            },
            onResize: () => this.computeJumpPresentPosition(),
            onScroll: this.onScroll,
        });
        useChildSubEnv({
            getCurrentThread: () => this.props.thread,
            onImageLoaded: this.threadScroll.applyScroll,
        });
    }
    _setupMessageEffects() {
        useEffect(
            /** @param {number} focus */
            (focus) => {
                if (focus && this.state.mountedAndLoaded) {
                    this.root.el.focus();
                }
            },
            () => [
                this.props.autofocus + this.props.thread.autofocus,
                this.state.mountedAndLoaded,
            ],
        );
        useEffect(
            () => {
                this.computeJumpPresentPosition();
            },
            () => [this.jumpPresentRef.el, this.state.showJumpPresent],
        );
        useEffect(
            () => this.updateShowJumpPresent(),
            () => [this.props.thread.loadNewer],
        );
        useEffect(
            () => {
                if (this.props.jumpPresent !== this.lastJumpPresent) {
                    this.jumpToPresent({ immediate: true });
                }
            },
            () => [this.props.jumpPresent],
        );
        useEffect(
            () => {
                if (this.props.thread.highlightMessage && this.state.mountedAndLoaded) {
                    log.logic("highlightMessage from thread", () => ({
                        thread: this.props.thread.localId,
                        messageId: this.props.thread.highlightMessage.id,
                    }));
                    this.messageHighlight?.highlightMessage(
                        this.props.thread.highlightMessage,
                        this.props.thread,
                    );
                    this.props.thread.highlightMessage = null;
                }
            },
            () => [this.props.thread.highlightMessage, this.state.mountedAndLoaded],
        );
        useEffect(
            () => {
                if (!this.state.mountedAndLoaded) {
                    return;
                }
                this.updateShowJumpPresent();
            },
            () => [this.state.mountedAndLoaded],
        );
        onMounted(() => {
            if (this.consumeChatterFetchRequest()) {
                log.lifecycle("mounted fetch", () => ({
                    thread: this.props.thread.localId,
                    inChatter: Boolean(this.env.chatter),
                }));
                this.fetchMessages();
            }
        });
        onWillUnmount(() => {
            if (this.props.thread.isFocusedByThread) {
                this.props.thread.isFocusedByThread = false;
            }
        });
    }
    _setupJumpEffects() {
        useEffect(
            /** @param {boolean} isLoaded */
            (isLoaded) => {
                this.state.mountedAndLoaded = isLoaded;
            },
            () => [this.props.thread.isLoaded, this.state.resetCount],
        );
        useEffect(
            () => {
                if (!this.props.jumpToNewMessage) {
                    return;
                }
                const separatorId = this.props.thread.newMessageSeparatorId;
                if (!separatorId) {
                    return;
                }
                let jumpMessage;
                for (const message of this.props.thread.messages) {
                    if (
                        message.persistent &&
                        Number(message.id) < separatorId &&
                        (!jumpMessage || message.id > jumpMessage.id)
                    ) {
                        jumpMessage = message;
                    }
                }
                const el = jumpMessage
                    ? this.refByMessageId.get(jumpMessage.id)?.el
                    : undefined;
                log.logic("jumpToNewMessage", () => ({
                    thread: this.props.thread.localId,
                    separatorId,
                    jumpMessageId: jumpMessage?.id,
                    found: Boolean(el),
                }));
                if (el) {
                    el.querySelector(".o-mail-Message-jumpTarget").scrollIntoView({
                        behavior: "instant",
                        block: "center",
                    });
                }
            },
            () => [this.props.jumpToNewMessage],
        );
    }
    _setupThreadListeners() {
        useBus(
            this.env.bus,
            "MAIL:RELOAD-THREAD",
            /** @param {CustomEvent<{model: string, id: number}>} ev */
            ({ detail }) => {
                const { model, id } = this.props.thread;
                if (detail.model === model && detail.id === id) {
                    log.pipeline("MAIL:RELOAD-THREAD", () => ({
                        thread: this.props.thread.localId,
                    }));
                    toRaw(this.props.thread).fetchNewMessages();
                }
            },
        );
        onWillUpdateProps(
            /** @param {{thread: import("models").Thread, jumpPresent: number}} nextProps */
            (nextProps) => {
                if (nextProps.thread.notEq(this.props.thread)) {
                    log.lifecycle("thread swapped", () => ({
                        from: this.props.thread.localId,
                        to: nextProps.thread.localId,
                    }));
                    this.lastJumpPresent = nextProps.jumpPresent;
                }
                if (this.consumeChatterFetchRequest()) {
                    toRaw(nextProps.thread).fetchNewMessages();
                }
            },
        );
    }
    setup() {
        useLifecycleLog(log);
        super.setup();
        this._setupServicesAndRefs();
        this._setupScrollTracking();
        this._setupMessageEffects();
        this._setupJumpEffects();
        this._setupThreadListeners();
    }

    computeJumpPresentPosition() {
        measure(() => {
            this._viewportEl = undefined;
            const viewportEl = this.viewportEl;
            const thresholdEl = this.presentThresholdRef.el;
            const jumpPresentEl = this.jumpPresentRef.el;
            if (!thresholdEl && !jumpPresentEl) {
                return;
            }
            const threshold = this.PRESENT_THRESHOLD;
            let transform;
            if (viewportEl && jumpPresentEl) {
                const width = viewportEl.clientWidth;
                const height = viewportEl.clientHeight;
                const computedStyle = window.getComputedStyle(viewportEl);
                const ps = parseInt(computedStyle.getPropertyValue("padding-left"));
                const pe = parseInt(computedStyle.getPropertyValue("padding-right"));
                const pt = parseInt(computedStyle.getPropertyValue("padding-top"));
                const pb = parseInt(computedStyle.getPropertyValue("padding-bottom"));
                transform = `translate(${
                    this.env.inChatter ? 22 : width - ps - pe - 22
                }px, ${
                    this.env.inChatter && !this.env.inChatter.aside
                        ? -22
                        : height - pt - pb - (this.env.inChatter?.aside ? 75 : 0)
                }px)`;
            }
            mutate(() => {
                if (thresholdEl?.isConnected) {
                    thresholdEl.style.height = `Min(${threshold}px, 100%)`;
                }
                if (transform && jumpPresentEl?.isConnected) {
                    jumpPresentEl.style.transform = transform;
                }
            });
        });
    }

    /** @param {import("models").Thread} thread */
    applyScrollContextually(thread) {
        this.threadScroll.applyScrollContextually(thread);
    }

    /** @type {import("@mail/core/common/thread_scroll_hook").ThreadScroll["isSmoothScrolling"]} */
    get isSmoothScrolling() {
        return this.threadScroll.isSmoothScrolling;
    }

    /** @type {import("@mail/core/common/thread_scroll_hook").ThreadScroll["smoothScrollingDeferred"]} */
    get smoothScrollingDeferred() {
        return this.threadScroll.smoothScrollingDeferred;
    }

    fetchMessages() {
        toRaw(this.props.thread).fetchNewMessages();
    }

    /** @returns {boolean} whether the messages of the thread should be fetched now */
    consumeChatterFetchRequest() {
        const chatter = this.env.chatter;
        if (!chatter) {
            return true;
        }
        if (!chatter.fetchMessages) {
            return false;
        }
        chatter.fetchMessages = false;
        return true;
    }

    /**
     * The scrollable element, or its first ancestor that fits the window. Walking up
     * reads `clientHeight` on every step, each a forced layout right after a patch, and
     * the template asks on every render; the answer is cached until this component
     * patches, and measured again for free by the ResizeObserver of
     * `useThreadScroll` (observing from mount, after layout) whenever the
     * scrollable resizes.
     */
    get viewportEl() {
        if (this._viewportEl?.isConnected) {
            return this._viewportEl;
        }
        let viewportEl = this.scrollableRef.el;
        while (viewportEl && viewportEl.clientHeight > browser.innerHeight) {
            viewportEl = viewportEl.parentElement;
        }
        this._viewportEl = viewportEl;
        return viewportEl;
    }

    get PRESENT_THRESHOLD() {
        const threshold =
            (this.viewportEl?.clientHeight ?? 0) * PRESENT_VIEWPORT_THRESHOLD;
        return this.state.showJumpPresent ? threshold - 200 : threshold;
    }

    updateShowJumpPresent() {
        this.state.showJumpPresent =
            this.visibleState.isVisible &&
            (this.props.thread.loadNewer ||
                this.presentThresholdState.isVisible === false);
    }

    onClickLoadOlder() {
        log.logic("onClickLoadOlder", () => ({ thread: this.props.thread.localId }));
        this.props.thread.fetchMoreMessages();
    }

    onFocusin() {
        this.props.thread.isFocusedByThread = true;
        markThreadAsReadIfAtBottom(this.props.thread);
    }

    onFocusout() {
        this.props.thread.isFocusedByThread = false;
    }

    /** @param {import("models").Message} [parentMessage] */
    async onParentMessageClick(parentMessage) {
        if (!parentMessage) {
            return;
        }
        const targetThread = parentMessage.thread;
        if (!targetThread) {
            return;
        }
        log.logic("onParentMessageClick", () => ({
            messageId: parentMessage.id,
            sameThread: targetThread.eq(this.props.thread),
            targetThread: targetThread.localId,
        }));
        if (targetThread.eq(this.props.thread)) {
            this.env.messageHighlight?.highlightMessage(parentMessage, targetThread);
        } else {
            targetThread.highlightMessage = parentMessage;
            await targetThread.open({ focus: true });
        }
    }

    /**
     * @param {import("models").Message} message
     * @returns {string}
     */
    getMessageClassName(message) {
        return !message.isNotification &&
            this.messageHighlight?.highlightedMessageId === message.id
            ? "o-highlighted bg-view shadow-lg pb-1"
            : "";
    }

    /**
     * @param {Object} [options]
     * @param {boolean} [options.immediate=false]
     */
    async jumpToPresent({ immediate = false } = {}) {
        log.logic("jumpToPresent", () => ({
            thread: this.props.thread.localId,
            immediate,
            loadNewer: this.props.thread.loadNewer,
        }));
        this.messageHighlight?.clear();
        if (!immediate || this.props.thread.loadNewer) {
            await this.props.thread.loadAround();
            this.props.thread.loadNewer = false;
            this.state.showJumpPresent = false;
        }
        this.props.thread.scrollTop = immediate ? "bottom" : "bottom-smooth";
        if (!this.ui.isSmall) {
            this.props.thread.composer.autofocus++;
        }
    }

    /**
     * @param {import("models").Message} message
     * @param {import("@odoo/owl").Ref|null} ref
     */
    registerMessageRef(message, ref) {
        if (!ref) {
            this.refByMessageId.delete(message.id);
            return;
        }
        this.refByMessageId.set(message.id, markRaw(ref));
    }

    /**
     * @param {import("models").Message} msg
     * @param {import("models").Message} [prevMsg]
     * @returns {boolean}
     */
    isSquashed(msg, prevMsg) {
        if (this.props.thread.isMailbox) {
            return false;
        }
        if (!prevMsg || prevMsg.message_type === "notification" || this.env.inChatter) {
            return false;
        }

        if (!msg.author?.eq(prevMsg.author)) {
            return false;
        }
        if (!msg.thread?.eq(prevMsg.thread)) {
            return false;
        }
        if (msg.isNote) {
            return false;
        }
        return msg.datetime.ts - prevMsg.datetime.ts < 5 * 60 * 1000;
    }

    onScroll() {
        if (!this.scrollableRef.el) {
            return;
        }
        this.threadScroll.saveScroll();
        this.state.scrollTop = this.scrollableRef.el.scrollTop;
        markThreadAsReadIfAtBottom(this.props.thread);
    }

    async scrollToHighlighted() {
        if (!this.messageHighlight?.highlightedMessageId || this.scrollingToHighlight) {
            return;
        }
        const el = this.refByMessageId.get(
            this.messageHighlight.highlightedMessageId,
        )?.el;
        if (el) {
            this.scrollingToHighlight = true;
            log.logic("scrollToHighlighted", () => ({
                thread: this.props.thread.localId,
                messageId: this.messageHighlight.highlightedMessageId,
            }));
            await this.messageHighlight.startupDeferred;
            this.messageHighlight
                .scrollTo(el.querySelector(".o-mail-Message-jumpTarget"))
                .then(() => (this.scrollingToHighlight = false));
        }
    }

    get orderedMessages() {
        const messages = this.state.mountedAndLoaded
            ? this.props.thread.messages
            : this.props.thread.phantomMessages;
        return this.props.order === "asc" ? [...messages] : [...messages].reverse();
    }

    get showLoadOlder() {
        return (
            this.props.thread.loadOlder &&
            this.props.thread.isLoaded &&
            !this.props.thread.isTransient &&
            !this.props.thread.hasLoadingFailed &&
            !this.messageHighlight?.initiated &&
            !this.messageHighlight?.highlightedMessageId
        );
    }

    /** @type {import("@mail/core/common/thread_scroll_hook").ThreadScroll["setScroll"]} */
    setScroll(value, options) {
        this.threadScroll.setScroll(value, options);
    }

    get showStartMessage() {
        return (
            this.state.mountedAndLoaded &&
            this.props.thread.hasStartOfConversationBanner
        );
    }

    get startMessageTitle() {
        return this.props.thread.conversationStartTitle;
    }

    get startMessageSubtitle() {
        return this.props.thread.conversationStartSubtitle;
    }
}
