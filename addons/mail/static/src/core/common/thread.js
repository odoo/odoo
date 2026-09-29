import { DateSection } from "@mail/core/common/date_section";
import { Message } from "@mail/core/common/message";
import { NotificationMessage } from "./notification_message";
import { MessageHighlightPlugin } from "@mail/core/common/message_highlight_plugin";
import {
    useChildRefs,
    useMaybePlugin,
    useMessageSelection,
    useVisible,
} from "@mail/utils/common/hooks";
import { useScrollManager } from "@mail/utils/common/scroll";
import { incrementFn } from "@mail/utils/common/signal";
import { useAncestors } from "@mail/core/common/ancestor_plugin";
import { assignGetter } from "@mail/utils/common/misc";

import {
    Component,
    computed,
    onMounted,
    onPatched,
    proxy,
    signal,
    t,
    useListener,
    useOnChange,
    usePlugin,
    useProps,
    useScope,
} from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { Transition } from "@web/core/transition";
import { UIPlugin } from "@web/core/ui/ui_plugin";
import { useBus, useService } from "@web/core/utils/hooks";
import { escape } from "@web/core/utils/strings";

export const PRESENT_VIEWPORT_THRESHOLD = 1;
/**
 * @typedef {Object} Props
 * @property {number} [jumpPresent=0]
 * @property {number} [jumpToNewMessage=0]
 * @property {"asc"|"desc"} [order="asc"]
 * @property {import("models").Thread} thread
 * @property {string} [searchTerm]
 * @property {import("@odoo/owl").Signal<HTMLElement>} [scrollRef]
 * @extends {Component<Props, Env>}
 */
export class Thread extends Component {
    static components = { Message, NotificationMessage, Transition, DateSection };
    static template = "mail.Thread";

    isFocused = signal(false);
    hasHighlightedMessage = computed(() =>
        this.orderedMessages.some((message) => this.isMessageHighlighted(message))
    );
    scope = useScope();
    /**
     * Message to scroll to, taking precedence over any other scroll.
     *
     * @type {import("@odoo/owl").ReactiveValue<import("@mail/utils/common/scroll").ScrollTarget|undefined>}
     */
    scrollTarget = computed(() => undefined);

    setup() {
        super.setup();
        this.ancestors = useAncestors({
            inThread: assignGetter(
                { onImageLoaded: () => this.scroll.apply() },
                { thread: () => this.props.thread }
            ),
        });
        this.escape = escape;
        this.onWheel = this.onWheel.bind(this);
        // bound once so `onParentMessageClick` is a stable (useProps.static) handler
        this.onParentMessageClick = this.onParentMessageClick.bind(this);
        this.startMessageAvatarRef = signal.ref(HTMLDivElement);
        this.messageRefs = useChildRefs();
        this.store = useService("mail.store");
        this.props = useProps({
            autofocus: t.or([t.number(), t.boolean()]).optional(),
            jumpPresent: t.number().optional(0),
            jumpToNewMessage: t.number().optional(),
            order: t.selection(["asc", "desc"]).optional("asc"),
            scrollRef: t.signal(t.instanceOf(HTMLElement)).optional(),
            showDates: t.boolean().optional(true),
            showEmptyMessage: t.boolean().optional(true),
            showJumpPresent: t.boolean().optional(true),
            thread: t.instanceOf(this.store["mail.thread"]),
        });
        this.ui = usePlugin(UIPlugin);
        this.state = proxy({
            isReplyingTo: false,
            mountedAndLoaded: false,
            showJumpPresent: false,
        });
        // before hooks depending on `mountedAndLoaded`, so they see it on mount
        onMounted(() => (this.state.mountedAndLoaded = this.props.thread.isLoaded));
        /**
         * Bumped by `reset()`. Observed by the rendering so that the patch
         * mirroring `isLoaded` into `mountedAndLoaded` follows a reset, without
         * making `mountedAndLoaded` depend on itself.
         */
        this.resetCount = signal(0);
        this.incrementResetCount = incrementFn(this.resetCount);
        this.lastJumpPresent = this.props.jumpPresent;
        this.messageHighlight = useMaybePlugin(MessageHighlightPlugin);
        this.present = signal.ref();
        this.jumpPresentRef = signal.ref();
        this.loadOlderRef = signal.ref();
        this.presentThresholdRef = signal.ref();
        this.rootRef = signal.ref(HTMLDivElement);
        this.visibleState = useVisible(this.rootRef, () => {
            this.updateShowJumpPresent();
        });
        /**
         * This is the reference element with the scrollbar. The reference can
         * either be the chatter scrollable (if chatter) or the thread
         * scrollable (in other cases).
         */
        this.scrollableRef = computed(() => this.props.scrollRef?.() ?? this.rootRef());
        this.loadOlderState = useVisible(
            this.loadOlderRef,
            async () => {
                await this.scroll.waitForIdle();
                if (this.loadOlderState.isVisible && this.shouldTriggerLoadOnVisible) {
                    this.props.thread.fetchMoreMessages();
                }
            },
            { ready: false }
        );
        this.loadNewerState = useVisible(
            this.present,
            async () => {
                await this.scroll.waitForIdle();
                if (this.loadNewerState.isVisible && this.shouldTriggerLoadOnVisible) {
                    this.props.thread.fetchMoreMessages({ epoch: "newer" });
                }
            },
            { ready: false }
        );
        this.messageSelection = useMessageSelection();
        this.presentThresholdState = useVisible(this.presentThresholdRef, () =>
            this.updateShowJumpPresent()
        );
        /**
         * These states need to be reset when the value changes on the record,
         * because the transition is important, not only the final value. If
         * resetting is depending on the update cycle, it can happen that the
         * value quickly changes and then back again before there is any
         * mounting/patching, and the change would therefore be undetected.
         * The batched effect is enough: it runs in the microtask following the
         * write, while the value only changes back once messages are fetched.
         */
        useOnChange(
            () => [this.props.thread.isLoaded],
            (isLoaded) => {
                if (!isLoaded || !this.state.mountedAndLoaded) {
                    this.reset();
                }
            },
            { initialRun: false }
        );
        this.scroll = useScrollManager({
            ref: this.scrollableRef,
            reversed: () => this.props.order === "desc",
            ready: () => this.props.thread.isLoaded && this.state.mountedAndLoaded,
            bounds: () => ({
                start: this.props.thread.oldestPersistentMessage?.id,
                end: this.props.thread.newestPersistentMessage?.id,
            }),
            hasMoreAfterEnd: () => this.props.thread.loadNewer,
            getPosition: () => this.props.thread.scrollTop,
            setPosition: (position) => (this.props.thread.scrollTop = position),
            getItemEl: (messageId) => this.messageRefs.get(messageId)?.(),
            getItemScrollTarget: (messageEl) =>
                messageEl.querySelector(".o-mail-Message-jumpTarget"),
            getFirstItemAfter: (messageId) =>
                this.channel?.getFirstNewerMessage({ from_message_id: messageId + 1 })?.id,
            getTarget: () => this.scrollTarget(),
            onTargetReached: (target) => this.onScrollTargetReached(target),
            getRevealedItem: () =>
                this.messageHighlight?.highlightedMessageId() && {
                    key: this.messageHighlight.highlightedMessageId(),
                    fromEnd: this.messageHighlight.isOlderThanLoaded(),
                },
            onNotReady: () => this.reset(),
            onFirstApply: () => {
                this.loadOlderState.ready = true;
                this.loadNewerState.ready = true;
            },
            onScroll: () => this.onScroll(),
        });
        useListener(this.scrollableRef, "wheel", this.onWheel);
        useOnChange(
            () => [this.props.autofocus + this.props.thread.autofocus, this.state.mountedAndLoaded],
            (focus, mountedAndLoaded) => {
                if (focus && mountedAndLoaded) {
                    this.rootRef().focus();
                }
            }
        );
        useOnChange(
            () => [this.jumpPresentRef(), this.viewportEl],
            () => this.computeJumpPresentPosition()
        );
        useOnChange(
            () => [this.props.thread.loadNewer],
            () => this.updateShowJumpPresent()
        );
        useOnChange(
            () => [this.props.jumpPresent],
            (jumpPresent) => {
                if (jumpPresent !== this.lastJumpPresent) {
                    this.jumpToPresent({ immediate: true });
                }
            }
        );
        useOnChange(
            () => [this.props.thread.highlightMessage, this.state.mountedAndLoaded],
            (highlightMessage, mountedAndLoaded) => {
                if (highlightMessage && mountedAndLoaded) {
                    this.messageHighlight?.highlightMessage(highlightMessage);
                    this.props.thread.highlightMessage = null;
                }
            }
        );
        useOnChange(
            () => [this.state.mountedAndLoaded],
            (mountedAndLoaded) => {
                if (mountedAndLoaded) {
                    this.updateShowJumpPresent();
                }
            }
        );
        const jumpPresentObserver = new ResizeObserver(() => this.computeJumpPresentPosition());
        useOnChange(
            () => [this.scrollableRef(), this.state.mountedAndLoaded],
            (el, mountedAndLoaded) => {
                if (el && mountedAndLoaded) {
                    jumpPresentObserver.observe(el);
                    return () => jumpPresentObserver.unobserve(el);
                }
            }
        );
        onMounted(() => {
            if (!this.ancestors.inChatter) {
                this.fetchInitialMessages();
            }
        });
        useOnChange(
            () => [this.props.thread, this.isFocused()],
            function onChangeIsFocused(thread, isFocused) {
                if (isFocused) {
                    thread.isFocusedCounter++;
                    return () => thread.isFocusedCounter--;
                }
            }
        );
        /**
         * Re-synced on each mount/patch, after `this.scroll.apply` (registered
         * before in `useScrollManager`): a `reset()` forcing `mountedAndLoaded`
         * false is followed by a render, as `resetCount` is observed by the
         * rendering.
         */
        const syncMountedAndLoaded = () => {
            this.state.mountedAndLoaded = this.props.thread.isLoaded;
        };
        onMounted(syncMountedAndLoaded);
        onPatched(syncMountedAndLoaded);
        const jumpToNewMessage = () => {
            if (!this.props.jumpToNewMessage) {
                return;
            }
            const el = this.messageRefs.get(
                this.channel?.self_member_id.new_message_separator_ui - 1
            )?.();
            if (el) {
                el.querySelector(".o-mail-Message-jumpTarget").scrollIntoView({
                    behavior: "instant",
                    block: "center",
                });
            }
        };
        // the messages are only there once mounted
        onMounted(jumpToNewMessage);
        useOnChange(() => [this.props.jumpToNewMessage], jumpToNewMessage, {
            initialRun: false,
        });
        useBus(this.env.bus, "MAIL:RELOAD-THREAD", ({ detail }) => {
            const { model, id } = this.props.thread;
            if (detail.model === model && detail.id === id) {
                this.props.thread.fetchNewMessages();
            }
        });
        useOnChange(
            () => [this.props.thread],
            (thread) => {
                this.lastJumpPresent = this.props.jumpPresent;
                if (!this.ancestors.inChatter) {
                    thread.fetchNewMessages();
                }
            },
            { initialRun: false }
        );
    }

    get channel() {
        return this.props.thread.channel;
    }

    get startMessageAvatarAttClass() {
        return {
            "o-mail-Thread-avatarChatWindow mt-1": this.ancestors.inChatWindow,
            "mt-2": !this.ancestors.inChatWindow,
        };
    }

    computeJumpPresentPosition() {
        if (!this.viewportEl || !this.jumpPresentRef()) {
            return;
        }
        const width = this.viewportEl.clientWidth;
        const height = this.viewportEl.clientHeight;
        const computedStyle = window.getComputedStyle(this.viewportEl);
        const ps = parseInt(computedStyle.getPropertyValue("padding-left"));
        const pe = parseInt(computedStyle.getPropertyValue("padding-right"));
        const pt = parseInt(computedStyle.getPropertyValue("padding-top"));
        const pb = parseInt(computedStyle.getPropertyValue("padding-bottom"));
        this.jumpPresentRef().style.transform = `translate(${
            this.ancestors.inChatter ? 22 : width - ps - pe - 22
        }px, ${
            this.ancestors.inChatter && !this.ancestors.inChatter.aside
                ? -22
                : height - pt - pb - (this.ancestors.inChatter?.aside ? 75 : 0)
        }px)`;
    }

    /**
     * @param {import("@mail/utils/common/scroll").ScrollTarget} _target
     */
    onScrollTargetReached(_target) {}

    fetchInitialMessages() {
        this.props.thread.fetchInitialMessages();
    }

    get viewportEl() {
        let viewportEl = this.scrollableRef();
        if (viewportEl && viewportEl.clientHeight > window.innerHeight) {
            while (viewportEl && viewportEl.clientHeight > window.innerHeight) {
                viewportEl = viewportEl.parentElement;
            }
        }
        return viewportEl;
    }

    get PRESENT_THRESHOLD() {
        const threshold = (this.viewportEl?.clientHeight ?? 0) * PRESENT_VIEWPORT_THRESHOLD;
        return this.state.showJumpPresent ? threshold - 200 : threshold;
    }

    updateShowJumpPresent() {
        this.state.showJumpPresent =
            this.visibleState.isVisible &&
            (this.props.thread.loadNewer || this.presentThresholdState.isVisible === false);
    }

    onClickLoadOlder() {
        if (this.messageHighlight?.highlightedMessageId()) {
            return;
        }
        this.props.thread.fetchMoreMessages();
    }

    get shouldTriggerLoadOnVisible() {
        return true;
    }

    onClickRetry() {
        if (!this.props.thread.oldestPersistentMessage) {
            this.fetchInitialMessages();
            return;
        }
        this.onClickLoadOlder();
    }

    onFocusin() {
        this.isFocused.set(true);
        if (this.props.thread.shouldMarkAsReadOnFocus) {
            this.props.thread.markAsRead();
        }
    }

    onFocusout() {
        this.isFocused.set(false);
    }

    /**
     * @type {ReturnType<typeof import("@mail/core/common/message_in_reply").onParentMessageClickType>["type"]}
     */
    async onParentMessageClick(ev, { parentAtRender }) {
        if (!parentAtRender) {
            return;
        }
        const targetThread = parentAtRender.thread;
        if (!targetThread) {
            return;
        }
        if (targetThread.eq(this.props.thread)) {
            this.messageHighlight?.highlightMessage(parentAtRender);
        } else {
            targetThread.highlightMessage = parentAtRender;
            await targetThread.open({ focus: true });
        }
    }

    /** @param {import("models").Message} message */
    isMessageHighlighted(message) {
        return (
            !message.isNotification && this.messageHighlight?.highlightedMessageId() === message.id
        );
    }

    /** @param {import("models").Message} message */
    getMessageClassName(message) {
        return this.isMessageHighlighted(message) ? "o-highlighted" : "";
    }

    async jumpToPresent({ immediate = false } = {}) {
        this.messageHighlight?.clear();
        if (!immediate || this.props.thread.loadNewer) {
            await this.props.thread.loadAround();
            this.props.thread.loadNewer = false;
            this.state.showJumpPresent = false;
        }
        this.props.thread.scrollTop = immediate ? "bottom" : "bottom-smooth";
        if (!this.ui.isSmall()) {
            this.props.thread.composer.autofocus++;
        }
    }

    reset() {
        this.state.mountedAndLoaded = false;
        // Bump `resetCount` (observed by the rendering) so a patch follows
        // and re-syncs `mountedAndLoaded`. Only when loaded: while `!isLoaded`,
        // `this.scroll.apply` resets on every patch, so an unconditional bump
        // would spin the render loop until the fetch resolves. When loaded the
        // bump re-renders once, the mirror sets `mountedAndLoaded` true and
        // `this.scroll.apply` stops resetting, so it converges.
        if (this.props.thread.isLoaded) {
            this.incrementResetCount();
        }
        this.loadOlderState.ready = false;
        this.loadNewerState.ready = false;
        this.scroll.reset();
    }

    isSquashed(msg, prevMsg) {
        if (!prevMsg || prevMsg.message_type === "notification" || this.ancestors.inChatter) {
            return false;
        }

        if (!msg.author?.eq(prevMsg.author)) {
            return false;
        }
        if (!msg.thread?.eq(prevMsg.thread)) {
            return false;
        }
        if (msg.message_type !== prevMsg.message_type) {
            return false;
        }
        if (msg.isNote) {
            return false;
        }
        return msg.datetime.ts - prevMsg.datetime.ts < 5 * 60 * 1000;
    }

    onWheel(ev) {
        if (this.messageSelection.size) {
            ev.stopPropagation();
            ev.preventDefault();
        }
    }

    shouldMarkAsReadOnScroll(thread) {
        return (
            this.scroll.isAtEnd &&
            !thread.channel?.markedAsUnread &&
            thread.isFocused &&
            !thread.markingAsRead
        );
    }

    onScroll() {
        if (this.shouldMarkAsReadOnScroll(this.props.thread)) {
            this.props.thread.markAsRead();
        }
    }

    /** Already loaded threads (e.g. prefetched) show their messages from the first render. */
    get showLoadedContent() {
        if (this.scope.status === 0 /* new */) {
            return this.props.thread.isLoaded;
        }
        return this.state.mountedAndLoaded;
    }

    get orderedMessages() {
        // ensure rendering observes resetCount to re-sync mountedAndLoaded when reset() is called
        void this.resetCount();
        // and the readiness of the load triggers, observed from the following patch
        void this.loadOlderState.ready;
        void this.loadNewerState.ready;
        const messages = this.showLoadedContent
            ? this.props.thread.messages
            : this.props.thread.phantomMessages;
        return this.props.order === "asc" ? [...messages] : [...messages].reverse();
    }

    get showLoadOlder() {
        return (
            this.props.thread.loadOlder &&
            this.props.thread.isLoaded &&
            !this.props.thread.isTransient &&
            !this.props.thread.hasLoadingFailed
        );
    }

    get loadMoreClass() {
        return { [this.loadMoreBtnClass]: true, "opacity-0": !this.showLoadedContent };
    }

    get loadOlderWrapperAttClass() {
        return {};
    }

    get loadMoreBtnClass() {
        return "btn btn-link";
    }

    get isInErrorState() {
        return this.props.thread.hasLoadingFailed;
    }

    get errorStateText() {
        return _t("An error occurred while loading messages.");
    }

    get startMessageChannelTypes() {
        return ["channel", "group", "chat"];
    }

    get showStartMessage() {
        return (
            this.showLoadedContent &&
            !this.props.thread.loadOlder &&
            this.startMessageChannelTypes.includes(this.channel?.channel_type)
        );
    }

    get startMessageTitle() {
        const channelName = this.channel?.displayName;
        if (this.channel?.parent_channel_id) {
            return channelName;
        }
        if (this.channel?.channel_type === "channel") {
            return _t("Welcome to #%(channelName)s!", { channelName });
        }
        return this.channel.displayName;
    }

    get startMessageSubtitle() {
        if (this.channel?.parent_channel_id) {
            const authorName = this.store["res.partner"].records
                .values()
                .find((partner) =>
                    partner.main_user_id?.eq(this.props.thread.channel.create_uid)
                )?.name;
            if (authorName) {
                return _t("Started by %(authorName)s", { authorName });
            }
        }
        if (this.channel?.channel_type === "channel") {
            return _t("This is the start of the #%(channelName)s channel", {
                channelName: this.channel.name,
            });
        }
        if (this.channel?.channel_type === "group") {
            return _t("This is the start of %(conversationName)s group", {
                conversationName: this.channel.displayName,
            });
        }
        return _t("This is the start of your direct chat with %(userName)s", {
            userName: this.channel.displayName,
        });
    }

    showNewMessageLine(msg, prevMsg) {
        return (
            msg.threadAsFirstUnread?.eq(this.props.thread) &&
            (prevMsg || this.channel?.markedAsUnread)
        );
    }
}
