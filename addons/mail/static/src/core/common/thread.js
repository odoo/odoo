import { useLayoutEffect, useSubEnv } from "@web/owl2/utils";
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

import {
    Component,
    computed,
    onMounted,
    proxy,
    signal,
    t,
    untrack,
    useListener,
    useOnChange,
    useProps,
} from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { Transition } from "@web/core/transition";
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

    setup() {
        super.setup();
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
        this.ui = useService("ui");
        this.state = proxy({
            isReplyingTo: false,
            mountedAndLoaded: false,
            showJumpPresent: false,
            scrollTop: null,
        });
        /**
         * Bumped by `reset()`. Used as a dependency of the effect mirroring
         * `isLoaded` into `mountedAndLoaded` so the mirror is re-synced after a
         * reset without making `mountedAndLoaded` depend on itself.
         */
        this.resetCount = signal(0);
        this.incrementResetCount = incrementFn(this.resetCount);
        this.lastJumpPresent = this.props.jumpPresent;
        this.orm = useService("orm");
        this.ui = useService("ui");
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
                    this.props.thread.fetchMoreMessages({
                        routeParams: this.messageFetchRouteParams,
                    });
                }
            },
            { ready: false }
        );
        this.loadNewerState = useVisible(
            this.present,
            async () => {
                await this.scroll.waitForIdle();
                if (this.loadNewerState.isVisible && this.shouldTriggerLoadOnVisible) {
                    this.props.thread.fetchMoreMessages({
                        epoch: "newer",
                        routeParams: this.messageFetchRouteParams,
                    });
                }
            },
            { ready: false }
        );
        this.messageSelection = useMessageSelection();
        this.presentThresholdState = useVisible(this.presentThresholdRef, () =>
            this.updateShowJumpPresent()
        );
        /**
         * These states need to be immediately reset when the value changes on
         * the record, because the transition is important, not only the final
         * value. If resetting is depending on the update cycle, it can happen
         * that the value quickly changes and then back again before there is
         * any mounting/patching, and the change would therefore be undetected.
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
            getTarget: () => this.scrollTarget,
            onTargetReached: (target) => this.onScrollTargetReached(target),
            getRevealedItem: () =>
                this.messageHighlight?.highlightedMessageId && {
                    key: this.messageHighlight.highlightedMessageId,
                    fromEnd: this.messageHighlight.isOlderThanLoaded,
                },
            onNotReady: () => this.reset(),
            onFirstApply: () => {
                this.loadOlderState.ready = true;
                this.loadNewerState.ready = true;
            },
            onScroll: () => this.onScroll(),
        });
        useSubEnv({
            getCurrentThread: () => this.props.thread,
            onImageLoaded: this.scroll.apply,
        });
        useListener(this.scrollableRef, "wheel", this.onWheel);
        useLayoutEffect(
            (focus) => {
                if (focus && this.state.mountedAndLoaded) {
                    this.rootRef().focus();
                }
            },
            () => [this.props.autofocus + this.props.thread.autofocus, this.state.mountedAndLoaded]
        );
        useLayoutEffect(
            () => {
                this.computeJumpPresentPosition();
            },
            () => [untrack(this.jumpPresentRef), untrack(() => this.viewportEl)]
        );
        useLayoutEffect(
            () => this.updateShowJumpPresent(),
            () => [this.props.thread.loadNewer]
        );
        useLayoutEffect(
            () => {
                if (this.props.jumpPresent !== this.lastJumpPresent) {
                    this.jumpToPresent({ immediate: true });
                }
            },
            () => [this.props.jumpPresent]
        );
        useLayoutEffect(
            () => {
                if (this.props.thread.highlightMessage && this.state.mountedAndLoaded) {
                    this.messageHighlight?.highlightMessage(this.props.thread.highlightMessage);
                    this.props.thread.highlightMessage = null;
                }
            },
            () => [this.props.thread.highlightMessage, this.state.mountedAndLoaded]
        );
        useLayoutEffect(
            () => {
                if (!this.state.mountedAndLoaded) {
                    return;
                }
                this.updateShowJumpPresent();
            },
            () => [this.state.mountedAndLoaded]
        );
        const jumpPresentObserver = new ResizeObserver(() => this.computeJumpPresentPosition());
        useLayoutEffect(
            (el, mountedAndLoaded) => {
                if (el && mountedAndLoaded) {
                    jumpPresentObserver.observe(el);
                    return () => jumpPresentObserver.unobserve(el);
                }
            },
            () => [this.scrollableRef(), this.state.mountedAndLoaded]
        );
        onMounted(() => {
            if (!this.env.inChatter) {
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
        useLayoutEffect(
            (isLoaded) => {
                this.state.mountedAndLoaded = isLoaded;
            },
            /**
             * `reset()` forces `mountedAndLoaded` false and this effect writes
             * it too, so it can't be its own dependency: `useLayoutEffect`
             * records dependencies before running the body, hence a `reset()`
             * landing while this effect is being applied would leave the
             * recorded value matching the current one and strand
             * `mountedAndLoaded` at false. Depend on `resetCount`, bumped by
             * `reset()`, so every reset re-syncs `mountedAndLoaded` with
             * `isLoaded`.
             */
            () => [this.props.thread.isLoaded, this.resetCount()]
        );
        useLayoutEffect(
            () => {
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
            },
            () => [this.props.jumpToNewMessage]
        );
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
                if (!this.env.inChatter) {
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
            "o-mail-Thread-avatarChatWindow mt-1": this.env.inChatWindow,
            "mt-2": !this.env.inChatWindow,
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
            this.env.inChatter ? 22 : width - ps - pe - 22
        }px, ${
            this.env.inChatter && !this.env.inChatter.aside
                ? -22
                : height - pt - pb - (this.env.inChatter?.aside ? 75 : 0)
        }px)`;
    }

    /**
     * Message to scroll to, taking precedence over any other scroll.
     *
     * @returns {import("@mail/utils/common/scroll").ScrollTarget|undefined}
     */
    get scrollTarget() {
        return undefined;
    }

    /**
     * @param {import("@mail/utils/common/scroll").ScrollTarget} target
     */
    onScrollTargetReached(target) {}

    get messageFetchRouteParams() {
        return this.env.messageFetchRouteParams;
    }

    fetchInitialMessages() {
        this.props.thread.fetchNewMessages({ routeParams: this.messageFetchRouteParams });
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
        if (this.messageHighlight?.highlightedMessageId) {
            return;
        }
        this.props.thread.fetchMoreMessages({ routeParams: this.messageFetchRouteParams });
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

    async onClickPreferences() {
        const actionDescription = await this.orm.call("res.users", "action_get");
        actionDescription.res_id = this.store.self_user?.id;
        this.env.services.action.doAction(actionDescription);
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

    getMessageClassName(message) {
        return !message.isNotification && this.messageHighlight?.highlightedMessageId === message.id
            ? "o-highlighted"
            : "";
    }

    async jumpToPresent({ immediate = false } = {}) {
        this.messageHighlight?.clear();
        if (!immediate || this.props.thread.loadNewer) {
            await this.props.thread.loadAround({ routeParams: this.messageFetchRouteParams });
            this.props.thread.loadNewer = false;
            this.state.showJumpPresent = false;
        }
        this.props.thread.scrollTop = immediate ? "bottom" : "bottom-smooth";
        if (!this.ui.isSmall) {
            this.props.thread.composer.autofocus++;
        }
    }

    reset() {
        this.state.mountedAndLoaded = false;
        // Bump `resetCount` (a mirror-effect dependency) so the effect re-runs
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
        if (!prevMsg || prevMsg.message_type === "notification" || this.env.inChatter) {
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

    get orderedMessages() {
        // ensure rendering observes resetCount to re-trigger the effect when reset() is called
        void this.resetCount();
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
            !this.props.thread.hasLoadingFailed
        );
    }

    get loadMoreClass() {
        return { [this.loadMoreBtnClass]: true, "opacity-0": !this.state.mountedAndLoaded };
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
            this.state.mountedAndLoaded &&
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
