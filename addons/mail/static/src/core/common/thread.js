import { DateSection } from "@mail/core/common/date_section";
import { Message } from "@mail/core/common/message";
import { Record } from "@mail/core/common/record";
import { useLoadMore, useVisible } from "@mail/utils/common/hooks";

import {
    Component,
    markRaw,
    onMounted,
    onWillDestroy,
    onWillPatch,
    onWillUpdateProps,
    reactive,
    toRaw,
    useChildSubEnv,
    useEffect,
    useRef,
    useState,
} from "@odoo/owl";
import { browser } from "@web/core/browser/browser";

import { _t } from "@web/core/l10n/translation";
import { Transition } from "@web/core/transition";
import { useBus, useRefListener, useService } from "@web/core/utils/hooks";
import { escape } from "@web/core/utils/strings";

export const PRESENT_VIEWPORT_THRESHOLD = 3;
const PRESENT_MESSAGE_THRESHOLD = 10;

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
        messageActions: true,
    };
    static template = "mail.Thread";

    setup() {
        super.setup();
        this.escape = escape;
        this.applyScroll = this.applyScroll.bind(this);
        this.saveScroll = this.saveScroll.bind(this);
        this.registerMessageRef = this.registerMessageRef.bind(this);
        this.store = useState(useService("mail.store"));
        this.state = useState({
            isReplyingTo: false,
            mountedAndLoaded: false,
            showJumpPresent: false,
            scrollTop: null,
        });
        this.lastJumpPresent = this.props.jumpPresent;
        this.orm = useService("orm");
        /** @type {ReturnType<import('@mail/utils/common/hooks').useMessageHighlight>|null} */
        this.messageHighlight = this.env.messageHighlight
            ? useState(this.env.messageHighlight)
            : null;
        this.scrollingToHighlight = false;
        this.refByMessageId = reactive(new Map(), () => this.scrollToHighlighted());
        useEffect(
            () => this.scrollToHighlighted(),
            () => [this.messageHighlight?.highlightedMessageId]
        );
        this.present = useRef("load-newer");
        this.jumpPresentRef = useRef("jump-present");
        this.root = useRef("messages");
        /**
         * This is the reference element with the scrollbar. The reference can
         * either be the chatter scrollable (if chatter) or the thread
         * scrollable (in other cases).
         */
        this.scrollableRef = this.props.scrollRef ?? this.root;
        useRefListener(
            this.scrollableRef,
            "scrollend",
            () => (this.state.scrollTop = this.scrollableRef.el.scrollTop)
        );
        this.loadOlderState = useLoadMore("load-older", {
            preCheck: () => this.messageHighlight?.scrollPromise,
            fn: () => toRaw(this.props.thread).fetchMoreMessages(),
            ready: false,
        });
        this.loadNewerState = useLoadMore("load-newer", {
            preCheck: () => this.messageHighlight?.scrollPromise,
            fn: () => toRaw(this.props.thread).fetchMoreMessages("newer"),
            ready: false,
        });
        this.presentThresholdState = useVisible("present-treshold", () =>
            this.updateShowJumpPresent()
        );
        this.setupScroll();
        useEffect(
            () => {
                this.computeJumpPresentPosition();
            },
            () => [this.jumpPresentRef.el, this.viewportEl]
        );
        useEffect(
            () => this.updateShowJumpPresent(),
            () => [this.props.thread.loadNewer]
        );
        useEffect(
            () => {
                if (this.props.jumpPresent !== this.lastJumpPresent) {
                    this.messageHighlight?.clearHighlight();
                    if (this.props.thread.loadNewer) {
                        this.jumpToPresent();
                    } else {
                        if (this.props.order === "desc") {
                            this.scrollableRef.el.scrollTop = 0;
                        } else {
                            this.scrollableRef.el.scrollTop =
                                this.scrollableRef.el.scrollHeight -
                                this.scrollableRef.el.clientHeight;
                        }
                        this.props.thread.scrollTop = "bottom";
                    }
                    this.lastJumpPresent = this.props.jumpPresent;
                }
            },
            () => [this.props.jumpPresent]
        );
        useEffect(
            () => {
                if (this.props.thread.highlightMessage && this.state.mountedAndLoaded) {
                    this.messageHighlight?.highlightMessage(
                        this.props.thread.highlightMessage,
                        this.props.thread
                    );
                    this.props.thread.highlightMessage = null;
                }
            },
            () => [this.props.thread.highlightMessage, this.state.mountedAndLoaded]
        );
        useEffect(
            () => {
                if (!this.state.mountedAndLoaded) {
                    return;
                }
                this.updateShowJumpPresent();
            },
            () => [this.state.mountedAndLoaded]
        );
        onMounted(() => {
            if (!this.env.chatter || this.env.chatter?.fetchMessages) {
                if (this.env.chatter) {
                    this.env.chatter.fetchMessages = false;
                }
                this.fetchMessages();
            }
        });
        useEffect(
            (isLoaded) => {
                this.state.mountedAndLoaded = isLoaded;
            },
            /**
             * Observe `mountedAndLoaded` as well because it might change from
             * other parts of the code without `useEffect` detecting any change
             * for `isLoaded`, and it should still be reset when patching.
             */
            () => [this.props.thread.isLoaded, this.state.mountedAndLoaded]
        );
        useBus(this.env.bus, "MAIL:RELOAD-THREAD", ({ detail }) => {
            const { model, id } = this.props.thread;
            if (detail.model === model && detail.id === id) {
                toRaw(this.props.thread).fetchNewMessages();
            }
        });
        onWillUpdateProps((nextProps) => {
            if (nextProps.thread.notEq(this.props.thread)) {
                this.lastJumpPresent = nextProps.jumpPresent;
            }
            if (!this.env.chatter || this.env.chatter?.fetchMessages) {
                if (this.env.chatter) {
                    this.env.chatter.fetchMessages = false;
                }
                toRaw(nextProps.thread).fetchNewMessages();
            }
        });
    }

    computeJumpPresentPosition() {
        if (!this.viewportEl || !this.jumpPresentRef.el) {
            return;
        }
        const width = this.viewportEl.clientWidth;
        const height = this.viewportEl.clientHeight;
        const computedStyle = window.getComputedStyle(this.viewportEl);
        const ps = parseInt(computedStyle.getPropertyValue("padding-left"));
        const pe = parseInt(computedStyle.getPropertyValue("padding-right"));
        const pt = parseInt(computedStyle.getPropertyValue("padding-top"));
        const pb = parseInt(computedStyle.getPropertyValue("padding-bottom"));
        this.jumpPresentRef.el.style.transform = `translate(${
            this.env.inChatter ? 22 : width - ps - pe - 22
        }px, ${
            this.env.inChatter && !this.env.inChatter.aside
                ? 0
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
         * after the first patch following when `mountedAndLoaded` is true. This
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
        /**
         * These states need to be immediately reset when the value changes on
         * the record, because the transition is important, not only the final
         * value. If resetting is depending on the update cycle, it can happen
         * that the value quickly changes and then back again before there is
         * any mounting/patching, and the change would therefore be undetected.
         */
        let stopOnChange = Record.onChange(this.props.thread, "isLoaded", () => {
            if (!this.props.thread.isLoaded || !this.state.mountedAndLoaded) {
                this.reset();
            }
        });
        onWillUpdateProps((nextProps) => {
            if (nextProps.thread.notEq(this.props.thread)) {
                stopOnChange();
                stopOnChange = Record.onChange(nextProps.thread, "isLoaded", () => {
                    if (!nextProps.thread.isLoaded || !this.state.mountedAndLoaded) {
                        this.reset();
                    }
                });
            }
        });
        onWillDestroy(() => stopOnChange());
        onWillPatch(() => {
            if (!this.loadedAndPatched) {
                return;
            }
            this.snapshot = {
                scrollHeight: this.scrollableRef.el.scrollHeight,
                scrollTop: this.scrollableRef.el.scrollTop,
            };
        });
        useEffect(this.applyScroll);
        useChildSubEnv({
            onImageLoaded: this.applyScroll,
        });
        const observer = new ResizeObserver(() => {
            this.computeJumpPresentPosition();
            this.applyScroll();
        });
        useEffect(
            (el, mountedAndLoaded) => {
                if (el && mountedAndLoaded) {
                    el.addEventListener("scroll", this.saveScroll);
                    observer.observe(el);
                    return () => {
                        observer.unobserve(el);
                        el.removeEventListener("scroll", this.saveScroll);
                    };
                }
            },
            () => [this.scrollableRef.el, this.state.mountedAndLoaded]
        );
    }

    applyScroll() {
        if (!this.props.thread.isLoaded || !this.state.mountedAndLoaded) {
            this.reset();
            return;
        }
        // Use toRaw() to prevent scroll check from triggering renders.
        const thread = toRaw(this.props.thread);
        this.applyScrollContextually(thread);
        this.snapshot = undefined;
        this.newestPersistentMessage = thread.newestPersistentMessage;
        this.oldestPersistentMessage = thread.oldestPersistentMessage;
        this.loadNewer = thread.loadNewer;
        if (!this.loadedAndPatched) {
            this.loadedAndPatched = true;
            this.loadOlderState.ready = true;
            this.loadNewerState.ready = true;
        }
    }

    /** @param {import("models").Thread} thread */
    applyScrollContextually(thread) {
        const olderMessages = thread.oldestPersistentMessage?.id < this.oldestPersistentMessage?.id;
        const newerMessages = thread.newestPersistentMessage?.id > this.newestPersistentMessage?.id;
        const messagesAtTop =
            (this.props.order === "asc" && olderMessages) ||
            (this.props.order === "desc" && newerMessages);
        const messagesAtBottom =
            (this.props.order === "desc" && olderMessages) ||
            (this.props.order === "asc" &&
                newerMessages &&
                (this.loadNewer || thread.scrollTop !== "bottom"));
        if (this.snapshot && messagesAtTop) {
            this.setScroll(
                this.snapshot.scrollTop +
                    this.scrollableRef.el.scrollHeight -
                    this.snapshot.scrollHeight
            );
        } else if (this.snapshot && messagesAtBottom) {
            this.setScroll(this.snapshot.scrollTop);
        } else if (
            !this.env.messageHighlight?.highlightedMessageId &&
            thread.scrollTop !== undefined
        ) {
            let value;
            if (thread.scrollTop === "bottom") {
                value =
                    this.props.order === "asc"
                        ? this.scrollableRef.el.scrollHeight - this.scrollableRef.el.clientHeight
                        : 0;
            } else {
                value =
                    this.props.order === "asc"
                        ? thread.scrollTop
                        : this.scrollableRef.el.scrollHeight -
                          thread.scrollTop -
                          this.scrollableRef.el.clientHeight;
            }
            if (this.lastSetValue === undefined || Math.abs(this.lastSetValue - value) > 1) {
                this.setScroll(value);
            }
        }
    }

    fetchMessages() {
        toRaw(this.props.thread).fetchNewMessages();
    }

    get viewportEl() {
        let viewportEl = this.scrollableRef.el;
        if (viewportEl && viewportEl.clientHeight > browser.innerHeight) {
            while (viewportEl && viewportEl.clientHeight > browser.innerHeight) {
                viewportEl = viewportEl.parentElement;
            }
        }
        return viewportEl;
    }

    get PRESENT_THRESHOLD() {
        const viewportHeight = (this.getViewportEl?.clientHeight ?? 0) * PRESENT_VIEWPORT_THRESHOLD;
        const messagesHeight = [...this.props.thread.nonEmptyMessages]
            .reverse()
            .slice(0, PRESENT_MESSAGE_THRESHOLD)
            .map((message) => this.refByMessageId.get(message.id))
            .reduce((totalHeight, message) => totalHeight + (message?.el?.clientHeight ?? 0), 0);
        const threshold = Math.max(viewportHeight, messagesHeight);
        return this.state.showJumpPresent ? threshold - 200 : threshold;
    }

    get preferenceButtonText() {
        const [, before, inside, after] =
            _t(
                "<button>Change your preferences</button> to receive new notifications in your inbox."
            ).match(/(.*)<button>(.*)<\/button>(.*)/) ?? [];
        return { before, inside, after };
    }

    updateShowJumpPresent() {
        this.state.showJumpPresent =
            this.props.thread.loadNewer || this.presentThresholdState.isVisible === false;
    }

    onClickLoadOlder() {
        this.props.thread.fetchMoreMessages();
    }

    async onClickPreferences() {
        const actionDescription = await this.orm.call("res.users", "action_get");
        actionDescription.res_id = this.store.self.userId;
        this.env.services.action.doAction(actionDescription);
    }

    getMessageClassName(message) {
        return !message.isNotification && this.messageHighlight?.highlightedMessageId === message.id
            ? "o-highlighted bg-view shadow-lg pb-1"
            : "";
    }

    async jumpToPresent() {
        this.messageHighlight?.clearHighlight();
        await this.props.thread.loadAround();
        this.props.thread.loadNewer = false;
        this.props.thread.scrollTop = "bottom";
        this.state.showJumpPresent = false;
    }

    registerMessageRef(message, ref) {
        if (!ref) {
            this.refByMessageId.delete(message.id);
            return;
        }
        this.refByMessageId.set(message.id, markRaw(ref));
    }

    reset() {
        this.state.mountedAndLoaded = false;
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
        if (
            !prevMsg ||
            prevMsg.message_type === "notification" ||
            prevMsg.isEmpty ||
            this.env.inChatter
        ) {
            return false;
        }

        if (!msg.author?.eq(prevMsg.author)) {
            return false;
        }
        if (!msg.thread?.eq(prevMsg.thread)) {
            return false;
        }
        return msg.datetime.ts - prevMsg.datetime.ts < 5 * 60 * 1000;
    }

    saveScroll() {
        const thread = toRaw(this.props.thread);
        const isBottom =
            this.props.order === "asc"
                ? this.scrollableRef.el.scrollHeight -
                      this.scrollableRef.el.scrollTop -
                      this.scrollableRef.el.clientHeight <
                  30
                : this.scrollableRef.el.scrollTop < 30;
        if (isBottom) {
            thread.scrollTop = "bottom";
        } else {
            thread.scrollTop =
                this.props.order === "asc"
                    ? this.scrollableRef.el.scrollTop
                    : this.scrollableRef.el.scrollHeight -
                      this.scrollableRef.el.scrollTop -
                      this.scrollableRef.el.clientHeight;
        }
    }

    scrollToHighlighted() {
        if (!this.messageHighlight?.highlightedMessageId || this.scrollingToHighlight) {
            return;
        }
        const el = this.refByMessageId.get(this.messageHighlight.highlightedMessageId)?.el;
        if (el) {
            this.scrollingToHighlight = true;
            this.messageHighlight.scrollTo(el).then(() => (this.scrollingToHighlight = false));
        }
    }

    get orderedMessages() {
        return this.props.order === "asc"
            ? [...this.props.thread.nonEmptyMessages]
            : [...this.props.thread.nonEmptyMessages].reverse();
    }

    setScroll(value) {
        this.scrollableRef.el.scrollTop = value;
        this.lastSetValue = value;
        this.saveScroll();
    }
}
