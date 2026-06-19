import { useChildSubEnv, useLayoutEffect } from "@web/owl2/utils";
import { DateSection } from "@mail/core/common/date_section";
import { Message } from "@mail/core/common/message";
import { NotificationMessage } from "./notification_message";
import {
    useChildRefs,
    useMessageSelection,
    useOnChange,
    useVisible,
} from "@mail/utils/common/hooks";

import {
    Component,
    computed,
    onMounted,
    onPatched,
    onWillPatch,
    onWillUnmount,
    props,
    proxy,
    signal,
    t,
    useListener,
} from "@odoo/owl";
import { browser } from "@web/core/browser/browser";

import { _t } from "@web/core/l10n/translation";
import { Transition } from "@web/core/transition";
import { useBus, useService } from "@web/core/utils/hooks";
import { escape } from "@web/core/utils/strings";

export const PRESENT_VIEWPORT_THRESHOLD = 1;
export class Thread extends Component {
    static components = { Message, NotificationMessage, Transition, DateSection };
    static template = "mail.Thread";

    setup() {
        super.setup();
        this.escape = escape;
        this.applyScroll = this.applyScroll.bind(this);
        this.saveScroll = this.saveScroll.bind(this);
        this.onScroll = this.onScroll.bind(this);
        this.onWheel = this.onWheel.bind(this);
        this.messageRefs = useChildRefs();
        this.store = useService("mail.store");
        this.props = props({
            autofocus: t.or([t.number(), t.boolean()]).optional(),
            jumpPresent: t.number().optional(0),
            jumpToNewMessage: t.number().optional(),
            order: t.selection(["asc", "desc"]).optional("asc"),
            scrollRef: t.signal(t.instanceOf(HTMLElement)).optional(),
            showDates: t.boolean().optional(true),
            showEmptyMessage: t.boolean().optional(true),
            showJumpPresent: t.boolean().optional(true),
            thread: t.instanceOf(this.store["mail.thread"].Class),
        });
        this.isSmoothScrolling = false;
        /**
         * Returns whether the current thread loaded its messages and it is the
         * thread currently present in the DOM. This is useful to know whether DOM
         * effect for the current thread can be applied already or if they need to
         * be delayed until the thread is actually loaded and patched in the DOM.
         */
        this.isThreadLoadedAndPatched = computed(
            () => this.props.thread.isLoaded && this.props.thread.eq(this.patchedThread())
        );
        /**
         * Forces the "jump to present" button to stay hidden after a jump, until the
         * thread actually reaches the present. {@link jumpToPresent} cannot wait for
         * the (smooth) scroll to land, so it raises this signal to hide the button
         * immediately; it is cleared once the present threshold becomes visible.
         */
        this.jumpPresentHidden = signal(false);
        this.jumpPresentRef = signal.ref(HTMLButtonElement);
        this.loadNewerRef = signal.ref(HTMLSpanElement);
        this.loadOlderRef = signal.ref(HTMLButtonElement);
        /**
         * Thread at the time of the last mount/patch. Useful to know whether the current thread
         * has been mounted/patched already.
         */
        this.patchedThread = signal(null, {
            type: t.instanceOf(this.store["mail.thread"].Class),
        });
        this.presentThresholdRef = signal.ref(HTMLSpanElement);
        this.rootRef = signal.ref(HTMLDivElement);
        /**
         * This is the reference element with the scrollbar. The reference can
         * either be the chatter scrollable (if chatter) or the thread
         * scrollable (in other cases).
         */
        this.scrollableRef = computed(() => this.props.scrollRef?.() ?? this.rootRef());
        this.showJumpPresent = computed(
            () =>
                !this.jumpPresentHidden() &&
                this.visibleState.isVisible &&
                (this.props.thread.loadNewer || this.presentThresholdState.isVisible === false)
        );
        /** @type {Promise|undefined} */
        this.smoothScrollingPromise;
        /** @type {number} */
        this.smoothScrollingTimeout;
        this.ui = useService("ui");
        this.state = proxy({
            isReplyingTo: false,
            scrollTop: null,
        });
        this.lastJumpPresent = this.props.jumpPresent;
        this.orm = useService("orm");
        this.ui = useService("ui");
        /** @type {ReturnType<import('@mail/utils/common/hooks').useMessageScrolling>|null} */
        this.messageHighlight = this.env.messageHighlight;
        // Scroll the highlighted message into view, driven reactively by the
        // highlighted message's own ref signal (set synchronously when the element
        // is patched in) rather than by observing the child-ref Map or a lifecycle
        // hook. The effect re-runs when the highlight changes, when its element
        // mounts, and when the message list grows/shrinks (to re-center as
        // surrounding messages load). It runs on the post-patch microtask, so the
        // element is in the DOM; `applyScroll` yields while a highlight is active
        // (see applyScrollContextually) so it cannot clobber this scroll.
        useOnChange(
            () => {
                const id = this.messageHighlight?.highlightedMessageId;
                return [id, id && this.messageRefs.get(id)?.(), this.props.thread.messages.length];
            },
            (id, el) => {
                const target = el?.querySelector?.(".o-mail-Message-jumpTarget");
                if (!target) {
                    return;
                }
                Promise.resolve(this.messageHighlight.startupPromise).then(() => {
                    if (this.messageHighlight?.highlightedMessageId === id) {
                        this.messageHighlight.scrollTo(target);
                    }
                });
            }
        );
        this.visibleState = useVisible(this.rootRef);
        useListener(
            this.scrollableRef,
            "scrollend",
            () => (this.state.scrollTop = this.scrollableRef().scrollTop)
        );
        this.loadOlderState = useVisible(this.loadOlderRef, () => this.loadOlderIfNeeded(), {
            ready: false,
        });
        this.loadNewerState = useVisible(this.loadNewerRef, () => this.loadNewerIfNeeded(), {
            ready: false,
        });
        // The load boundaries are watched through an IntersectionObserver, which
        // only fires on visibility changes, and loading is held off while a
        // message is highlighted (the highlight owns the scroll, see
        // `isHighlighting`). A boundary that scrolled into view during the
        // highlight would therefore never load once the highlight clears, as
        // there is no new visibility change to react to (e.g. scrolling to the
        // bottom right after jumping to a pinned message). Re-check the
        // boundaries when the highlight ends to resume the pending load.
        useOnChange(
            () => [this.isHighlighting],
            (isHighlighting) => {
                if (!isHighlighting) {
                    this.loadOlderIfNeeded();
                    this.loadNewerIfNeeded();
                }
            }
        );
        this.messageSelection = useMessageSelection();
        this.presentThresholdState = useVisible(this.presentThresholdRef, (isVisible) => {
            if (isVisible) {
                this.jumpPresentHidden.set(false);
            }
        });
        this.setupScroll();
        useLayoutEffect(
            (focus, isThreadLoadedAndPatched) => {
                if (focus && isThreadLoadedAndPatched) {
                    this.rootRef().focus();
                }
            },
            () => [
                this.props.autofocus + this.props.thread.autofocus,
                this.isThreadLoadedAndPatched(),
            ]
        );
        useLayoutEffect(
            () => {
                this.computeJumpPresentPosition();
            },
            () => [this.jumpPresentRef(), this.viewportEl]
        );
        useLayoutEffect(
            (jumpPresent) => {
                if (jumpPresent !== this.lastJumpPresent) {
                    this.jumpToPresent({ immediate: true });
                }
            },
            () => [this.props.jumpPresent]
        );
        useLayoutEffect(
            (highlightMessage, isThreadLoadedAndPatched) => {
                if (highlightMessage && isThreadLoadedAndPatched) {
                    this.messageHighlight?.highlightMessage(highlightMessage);
                    this.props.thread.highlightMessage = null;
                }
            },
            () => [this.props.thread.highlightMessage, this.isThreadLoadedAndPatched()]
        );
        onMounted(() => {
            this.patchedThread.set(this.props.thread);
            // In a chatter, (re)fetch only when the form controller asks for
            // it, to avoid fetching the same messages twice on load.
            if (!this.env.chatter || this.env.chatter.shouldFetchMessages) {
                if (this.env.chatter) {
                    this.env.chatter.shouldFetchMessages = false;
                }
                this.fetchInitialMessages();
            }
        });
        onPatched(() => this.patchedThread.set(this.props.thread));
        onWillUnmount(() => {
            if (this.props.thread.isFocusedByThread) {
                this.props.thread.isFocusedByThread = false;
            }
        });
        useLayoutEffect(
            (jumpToNewMessage) => {
                if (!jumpToNewMessage) {
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
        let fetchedThread = this.props.thread;
        useOnChange(
            () => [this.props.thread],
            (thread) => {
                if (thread.eq(fetchedThread)) {
                    return;
                }
                fetchedThread = thread;
                this.lastJumpPresent = this.props.jumpPresent;
                // In a chatter, (re)fetch only when the form controller asks for
                // it, to avoid fetching the same messages twice on load.
                if (!this.env.chatter || this.env.chatter.shouldFetchMessages) {
                    if (this.env.chatter) {
                        this.env.chatter.shouldFetchMessages = false;
                    }
                    this.fetchInitialMessages();
                }
            },
            { initialRun: false }
        );
    }

    get channel() {
        return this.props.thread.channel;
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
     * The scroll on a message list is managed in several different ways.
     *
     * 1. When the user first accesses a thread with unread messages, or when
     *    the user goes back to a thread with new unread messages, it should
     *    scroll to the position of the first unread message if there is one.
     * 2. When loading older or newer messages, the messages already on screen
     *    should visually stay in place. When the extra messages are added at
     *    the bottom (chatter loading older, or channel loading newer) the same
     *    scroll top position should be kept, and when the extra messages are
     *    added at the top (chatter loading newer, or channel loading older),
     *    the extra height from the extra messages should be compensated in the
     *    scroll position.
     * 3. When the scroll is at the bottom, it should stay at the bottom when
     *    there is a change of height: new messages, images loaded, ...
     * 4. When the user goes back and forth between threads, it should restore
     *    the last scroll position of each thread.
     * 5. When currently highlighting a message it takes priority to allow the
     *    highlighted message to be scrolled to.
     */
    setupScroll() {
        /**
         * Last scroll value that was automatically set. This prevents from
         * setting the same value 2 times in a row. This is not supposed to have
         * an effect, unless the value was changed from outside in the meantime,
         * in which case resetting the value would incorrectly override the
         * other change. This should give enough time to scroll/resize event to
         * register the new scroll value.
         */
        this.lastSetValue = undefined;
        /**
         * The snapshot mechanism (point 2) should only apply after the messages
         * have been loaded and displayed at least once. Technically this is
         * after the first patch following when `isThreadLoadedAndPatched` is true. This
         * is what this variable holds.
         */
        this.loadedAndPatched = false;
        /**
         * The snapshot of current scrollTop and scrollHeight for the purpose
         * of keeping messages in place when loading older/newer (point 2).
         */
        this.snapshot = undefined;
        /**
         * The newest message that is already rendered, useful to detect
         * whether newer messages have been loaded since last render to decide
         * when to apply the snapshot to keep messages in place (point 2).
         */
        this.newestPersistentMessage = undefined;
        /**
         * The oldest message that is already rendered, useful to detect
         * whether older messages have been loaded since last render to decide
         * when to apply the snapshot to keep messages in place (point 2).
         */
        this.oldestPersistentMessage = undefined;
        /**
         * Whether it was possible to load newer messages in the last rendered
         * state, useful to decide when to apply the snapshot to keep messages
         * in place (point 2).
         */
        this.loadNewer = undefined;
        useOnChange(
            () => [this.isThreadLoadedAndPatched()],
            (isThreadLoadedAndPatched) => {
                if (!isThreadLoadedAndPatched) {
                    this.reset();
                }
            }
        );
        onWillPatch(() => {
            if (!this.loadedAndPatched) {
                return;
            }
            this.snapshot = {
                scrollHeight: this.scrollableRef().scrollHeight,
                scrollTop: this.scrollableRef().scrollTop,
            };
        });
        useLayoutEffect(this.applyScroll);
        useChildSubEnv({
            getCurrentThread: () => this.props.thread,
            onImageLoaded: this.applyScroll,
        });
        const observer = new ResizeObserver(() => {
            this.computeJumpPresentPosition();
            this.applyScroll();
        });
        useLayoutEffect(
            (el, isThreadLoadedAndPatched) => {
                if (el && isThreadLoadedAndPatched) {
                    el.addEventListener("scroll", this.onScroll);
                    el.addEventListener("wheel", this.onWheel);
                    observer.observe(el);
                    return () => {
                        observer.unobserve(el);
                        el.removeEventListener("scroll", this.onScroll);
                        el.removeEventListener("wheel", this.onWheel);
                    };
                }
            },
            () => [this.scrollableRef(), this.isThreadLoadedAndPatched()]
        );
    }

    applyScroll() {
        if (!this.props.thread.isLoaded || !this.isThreadLoadedAndPatched()) {
            this.reset();
            return;
        }
        this.applyScrollContextually(this.props.thread);
        this.snapshot = undefined;
        this.newestPersistentMessage = this.props.thread.newestPersistentMessage;
        this.oldestPersistentMessage = this.props.thread.oldestPersistentMessage;
        this.loadNewer = this.props.thread.loadNewer;
        if (!this.loadedAndPatched) {
            this.loadedAndPatched = true;
            this.loadOlderState.ready = true;
            this.loadNewerState.ready = true;
        }
        // Release a highlight startup even if no `setScroll` ran this cycle (e.g.
        // already at the right position, or a keep-in-place branch was skipped
        // while highlighting); otherwise the awaited `startupPromise` would never
        // resolve and the highlight scroll would never start.
        this.messageHighlight?.resolveStartup?.();
    }

    /** @param {import("models").Thread} thread */
    applyScrollContextually(thread) {
        // A scroll-to-highlight owns the scroll position from the moment it starts
        // loading (`initiated`, before `highlightedMessageId` is set) until the
        // highlight is cleared. The keep-in-place (snapshot) branches must yield for
        // that whole window, else they clobber the in-flight jump. The final
        // `bottom`/scrollTop branch only yields once a message is actually
        // highlighted, so the startup still scrolls to the bottom (its precondition,
        // which also resolves `startupPromise`).
        const initiated = Boolean(this.env.messageHighlight?.initiated);
        const highlighted = Boolean(this.env.messageHighlight?.highlightedMessageId);
        const olderMessages = thread.oldestPersistentMessage?.id < this.oldestPersistentMessage?.id;
        const newerMessages = thread.newestPersistentMessage?.id > this.newestPersistentMessage?.id;
        const messagesAtTop =
            (this.props.order === "asc" && olderMessages) ||
            (this.props.order === "desc" && newerMessages);
        const messagesAtBottom =
            (this.props.order === "desc" && olderMessages) ||
            (this.props.order === "asc" &&
                newerMessages &&
                (this.loadNewer ||
                    typeof thread.scrollTop !== "string" ||
                    !thread.scrollTop?.includes("bottom")));
        if (!initiated && !highlighted && this.snapshot && messagesAtTop) {
            this.setScroll(
                this.snapshot.scrollTop +
                    this.scrollableRef().scrollHeight -
                    this.snapshot.scrollHeight
            );
        } else if (!initiated && !highlighted && this.snapshot && messagesAtBottom) {
            this.setScroll(this.snapshot.scrollTop);
        } else if (!highlighted && thread.scrollTop !== undefined) {
            let value;
            if (typeof thread.scrollTop === "string" && thread.scrollTop?.includes("bottom")) {
                if (newerMessages && this.channel) {
                    if (this.applyScrollContextuallyNewerChannelMessages(thread)) {
                        return;
                    }
                }
                value =
                    this.props.order === "asc"
                        ? this.scrollableRef().scrollHeight - this.scrollableRef().clientHeight
                        : 0;
            } else {
                value =
                    this.props.order === "asc"
                        ? thread.scrollTop
                        : this.scrollableRef().scrollHeight -
                          thread.scrollTop -
                          this.scrollableRef().clientHeight;
            }
            if (
                (this.lastSetValue === undefined || Math.abs(this.lastSetValue - value) > 1) &&
                !this.isSmoothScrolling
            ) {
                this.setScroll(value, {
                    smooth:
                        typeof thread.scrollTop === "string" &&
                        thread.scrollTop?.includes("smooth"),
                });
            }
        }
    }

    /**
     * @param {import("models").Thread} thread
     * @returns {Boolean} true when fully handled, false otherwise.
     */
    applyScrollContextuallyNewerChannelMessages(thread) {
        const firstNewerMessage = this.channel.getFirstNewerMessage({
            from_message_id: this.newestPersistentMessage.id + 1,
        });
        if (!firstNewerMessage) {
            return false;
        }
        const firstNewestMessageEl = this.messageRefs.get(firstNewerMessage.id)?.();
        if (!firstNewestMessageEl) {
            return false;
        }
        firstNewestMessageEl.querySelector(".o-mail-Message-jumpTarget").scrollIntoView({
            behavior: "instant",
            block: this.props.order === "asc" ? "start" : "end",
        });
        thread.scrollTop = this.isAtBottom ? "bottom" : this.scrollableRef().scrollTop;
        return true;
    }

    get messageFetchRouteParams() {
        return this.env.messageFetchRouteParams;
    }

    fetchInitialMessages() {
        this.props.thread.fetchNewMessages({ routeParams: this.messageFetchRouteParams });
    }

    get viewportEl() {
        let viewportEl = this.scrollableRef();
        if (viewportEl && viewportEl.clientHeight > browser.innerHeight) {
            while (viewportEl && viewportEl.clientHeight > browser.innerHeight) {
                viewportEl = viewportEl.parentElement;
            }
        }
        return viewportEl;
    }

    get PRESENT_THRESHOLD() {
        const threshold = (this.viewportEl?.clientHeight ?? 0) * PRESENT_VIEWPORT_THRESHOLD;
        return this.showJumpPresent() ? threshold - 200 : threshold;
    }

    /**
     * Whether a message highlight is in progress, from the moment it starts
     * loading (`initiated`, before `highlightedMessageId` is set) until it is
     * cleared. While highlighting, loading more messages must be held off: the
     * highlight owns the scroll (point 5) and growing the message list would
     * shift the height and clobber the in-flight scroll to the highlight.
     */
    get isHighlighting() {
        return Boolean(
            this.messageHighlight?.initiated || this.messageHighlight?.highlightedMessageId
        );
    }

    async loadOlderIfNeeded() {
        await Promise.all([this.messageHighlight?.scrollPromise, this.smoothScrollingPromise]);
        if (this.loadOlderState.isVisible && !this.isHighlighting) {
            this.props.thread.fetchMoreMessages({ routeParams: this.messageFetchRouteParams });
        }
    }

    async loadNewerIfNeeded() {
        await Promise.all([this.messageHighlight?.scrollPromise, this.smoothScrollingPromise]);
        if (this.loadNewerState.isVisible && !this.isHighlighting) {
            this.props.thread.fetchMoreMessages({
                epoch: "newer",
                routeParams: this.messageFetchRouteParams,
            });
        }
    }

    onClickLoadOlder() {
        if (this.isHighlighting) {
            return;
        }
        this.props.thread.fetchMoreMessages({ routeParams: this.messageFetchRouteParams });
    }

    onClickRetry() {
        this.onClickLoadOlder();
    }

    async onClickPreferences() {
        const actionDescription = await this.orm.call("res.users", "action_get");
        actionDescription.res_id = this.store.self_user?.id;
        this.env.services.action.doAction(actionDescription);
    }

    onFocusin() {
        this.props.thread.isFocusedByThread = true;
        if (this.props.thread.shouldMarkAsReadOnFocus) {
            this.props.thread.markAsRead();
        }
    }

    onFocusout() {
        this.props.thread.isFocusedByThread = false;
    }

    async onParentMessageClick(parentMessage) {
        if (!parentMessage) {
            return;
        }
        const targetThread = parentMessage.thread;
        if (!targetThread) {
            return;
        }
        if (targetThread.eq(this.props.thread)) {
            this.env.messageHighlight?.highlightMessage(parentMessage, targetThread);
        } else {
            targetThread.highlightMessage = parentMessage;
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
            // A concurrent reply-jump may have resolved its highlight during the
            // await above (re-setting `highlightedMessageId` after the clear at the
            // start). Clear again so the highlight does not block the scroll to
            // present below.
            this.messageHighlight?.clear();
            this.props.thread.loadNewer = false;
            this.jumpPresentHidden.set(true);
        }
        this.props.thread.scrollTop = immediate ? "bottom" : "bottom-smooth";
        if (!this.ui.isSmall) {
            this.props.thread.composer.autofocus++;
        }
    }

    reset() {
        this.loadOlderState.ready = false;
        this.loadNewerState.ready = false;
        this.lastSetValue = undefined;
        this.snapshot = undefined;
        this.newestPersistentMessage = undefined;
        this.oldestPersistentMessage = undefined;
        this.loadedAndPatched = false;
        this.loadNewer = false;
    }

    isSquashed(msg, prevMsg) {
        if (this.props.thread.model === "mail.box") {
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

    get isAtBottom() {
        if (this.loadNewer) {
            return false;
        }
        return this.props.order === "asc"
            ? this.scrollableRef().scrollHeight -
                  this.scrollableRef().scrollTop -
                  this.scrollableRef().clientHeight <
                  30
            : this.scrollableRef().scrollTop < 30;
    }

    onWheel(ev) {
        if (this.messageSelection.size) {
            ev.stopPropagation();
            ev.preventDefault();
        }
    }

    shouldMarkAsReadOnScroll(thread) {
        return (
            this.isAtBottom &&
            !thread.channel?.markedAsUnread &&
            thread.isFocused &&
            !thread.markingAsRead
        );
    }

    onScroll() {
        if (this.shouldMarkAsReadOnScroll(this.props.thread)) {
            this.props.thread.markAsRead();
        }
        this.saveScroll();
    }

    saveScroll() {
        const isBottom = this.isAtBottom;
        if (isBottom) {
            this.props.thread.scrollTop = "bottom";
        } else {
            this.props.thread.scrollTop =
                this.props.order === "asc"
                    ? this.scrollableRef().scrollTop
                    : this.scrollableRef().scrollHeight -
                      this.scrollableRef().scrollTop -
                      this.scrollableRef().clientHeight;
        }
    }

    get orderedMessages() {
        const messages = this.isThreadLoadedAndPatched()
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

    get isInErrorState() {
        return this.props.thread.hasLoadingFailed;
    }

    get errorStateText() {
        return _t("An error occurred while loading messages.");
    }
    setScroll(value, { smooth = false } = {}) {
        if (smooth) {
            clearTimeout(this.smoothScrollingTimeout);
            this.isSmoothScrolling = true;
            const { promise, resolve: resolveSmoothScrolling } = Promise.withResolvers();
            this.smoothScrollingPromise = promise;
            const onSmoothScrollingEnd = () => {
                resolveSmoothScrolling();
                this.smoothScrollingPromise = undefined;
                this.isSmoothScrolling = false;
            };
            if ("onscrollend" in window) {
                document.addEventListener("scrollend", onSmoothScrollingEnd, {
                    capture: true,
                    once: true,
                });
            } else {
                // To remove when safari will support the "scrollend" event.
                this.smoothScrollingTimeout = setTimeout(onSmoothScrollingEnd, 250);
            }
        }
        this.scrollableRef().scrollTo({ behavior: smooth ? "smooth" : undefined, top: value });
        this.lastSetValue = value;
        this.messageHighlight?.resolveStartup?.();
        this.saveScroll();
    }

    get showStartMessage() {
        return (
            this.isThreadLoadedAndPatched() &&
            !this.props.thread.loadOlder &&
            ["channel", "group", "chat"].includes(this.channel?.channel_type)
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
            const authorName = Object.values(this.store["res.partner"].records).find((partner) =>
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
}
