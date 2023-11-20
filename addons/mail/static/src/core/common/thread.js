/* @odoo-module */

import { DateSection } from "@mail/core/common/date_section";
import { Message } from "@mail/core/common/message";
import { useVisible } from "@mail/utils/common/hooks";

import {
    Component,
    onMounted,
    onWillPatch,
    onWillUpdateProps,
    toRaw,
    useChildSubEnv,
    useEffect,
    useRef,
    useState,
} from "@odoo/owl";

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
        messageActions: true,
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
        this.lastJumpPresent = this.props.jumpPresent;
        this.threadService = useState(useService("mail.thread"));
        /** @type {ReturnType<import('@mail/utils/common/hooks').useMessageHighlight>|null} */
        this.messageHighlight = this.env.messageHighlight
            ? useState(this.env.messageHighlight)
            : null;
        this.present = useRef("load-newer");
        /**
         * This is the reference element with the scrollbar. The reference can
         * either be the chatter scrollable (if chatter) or the thread
         * scrollable (in other cases).
         */
        this.scrollableRef = this.props.scrollRef ?? useRef("messages");
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
        this.setupScroll();
        useEffect(
            () => this.updateShowJumpPresent(),
            () => [this.props.thread.loadNewer]
        );
        useEffect(
            () => {
                if (this.props.jumpPresent !== this.lastJumpPresent) {
                    if (this.props.thread.loadNewer) {
                        this.jumpToPresent("instant");
                    } else {
                        if (this.props.order === "desc") {
                            this.scrollableRef.el.scrollTop = 0;
                            this.props.thread.scrollTop = 0;
                        } else {
                            this.scrollableRef.el.scrollTop =
                                this.scrollableRef.el.scrollHeight -
                                this.scrollableRef.el.clientHeight;
                            this.props.thread.scrollTop = "bottom";
                        }
                    }
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
                if (!this.env.inChatter) {
                    this.updateShowJumpPresent();
                }
            },
            () => [this.state.mountedAndLoaded]
        );
        onMounted(async () => {
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

    /**
     * The scroll on a message list is managed in several different ways.
     *
     * 1. When loading older or newer messages, the messages already on screen
     *    should visually stay in place. When the extra messages are added at
     *    the bottom (chatter loading older, or channel loading newer) the same
     *    scroll top position should be kept, and when the extra messages are
     *    added at the top (chatter loading newer, or channel loading older),
     *    the extra height from the extra messages should be compensated in the
     *    scroll position.
     * 2. When the scroll is at the bottom, it should stay at the bottom when
     *    there is a change of height: new messages, images loaded, ...
     * 3. When the user goes back and forth between threads, it should restore
     *    the last scroll position of each thread.
     * 4. When currently highlighting a message it takes priority to allow the
     *    highlighted message to be scrolled to.
     */
    setupScroll() {
        const ref = this.scrollableRef;
        /**
         * Last scroll value that was automatically set. This prevents from
         * setting the same value 2 times in a row. This is not supposed to have
         * an effect, unless the value was changed from outside in the meantime,
         * in which case resetting the value would incorrectly override the
         * other change. This should give enough time to scroll/resize event to
         * register the new scroll value.
         */
        let lastSetValue;
        /**
         * The snapshot mechanism (point 1) should only apply after the messages
         * have been loaded and displayed at least once. Technically this is
         * after the first patch following when `mountedAndLoaded` is true. This
         * is what this variable holds.
         */
        let loadedAndPatched = false;
        /**
         * The snapshot of current scrollTop and scrollHeight for the purpose
         * of keeping messages in place when loading older/newer (point 1).
         */
        let snapshot;
        /**
         * The newest message that is already rendered, useful to detect
         * whether newer messages have been loaded since last render to decide
         * when to apply the snapshot to keep messages in place (point 1).
         */
        let newestPersistentMessage;
        /**
         * The oldest message that is already rendered, useful to detect
         * whether older messages have been loaded since last render to decide
         * when to apply the snapshot to keep messages in place (point 1).
         */
        let oldestPersistentMessage;
        /**
         * Whether it was possible to load newer messages in the last rendered
         * state, useful to decide when to apply the snapshot to keep messages
         * in place (point 1).
         */
        let loadNewer;
        const saveScroll = () => {
            this.props.thread.scrollTop =
                ref.el.scrollHeight - ref.el.scrollTop - ref.el.clientHeight < 30
                    ? "bottom"
                    : ref.el.scrollTop;
        };
        const setScroll = (value) => {
            ref.el.scrollTop = value;
            lastSetValue = value;
            saveScroll();
        };
        const applyScroll = () => {
            if (this.state.mountedAndLoaded) {
                loadedAndPatched = true;
            } else {
                return;
            }
            // Use toRaw() to prevent scroll check from triggering renders.
            const thread = toRaw(this.props.thread);
            const olderMessages = thread.oldestPersistentMessage?.id < oldestPersistentMessage?.id;
            const newerMessages = thread.newestPersistentMessage?.id > newestPersistentMessage?.id;
            const messagesAtTop =
                (this.props.order === "asc" && olderMessages) ||
                (this.props.order === "desc" && newerMessages);
            const messagesAtBottom =
                (this.props.order === "desc" && olderMessages) ||
                (this.props.order === "asc" &&
                    newerMessages &&
                    (loadNewer || thread.scrollTop !== "bottom"));
            if (snapshot && !this.isJumpingRecent && messagesAtTop) {
                setScroll(snapshot.scrollTop + ref.el.scrollHeight - snapshot.scrollHeight);
            } else if (snapshot && !this.isJumpingRecent && messagesAtBottom) {
                setScroll(snapshot.scrollTop);
            } else if (
                !this.env.messageHighlight?.highlightedMessageId &&
                thread.scrollTop !== undefined
            ) {
                const value =
                    thread.scrollTop === "bottom"
                        ? ref.el.scrollHeight - ref.el.clientHeight
                        : thread.scrollTop;
                if (lastSetValue === undefined || Math.abs(lastSetValue - value) > 1) {
                    setScroll(value);
                }
            }
            snapshot = undefined;
            newestPersistentMessage = thread.newestPersistentMessage;
            oldestPersistentMessage = thread.oldestPersistentMessage;
            loadNewer = thread.loadNewer;
        };
        onWillPatch(() => {
            if (!loadedAndPatched) {
                return;
            }
            snapshot = {
                scrollHeight: ref.el.scrollHeight,
                scrollTop: ref.el.scrollTop,
            };
        });
        useEffect(applyScroll);
        useChildSubEnv({ onImageLoaded: applyScroll });
        const observer = new ResizeObserver(applyScroll);
        useEffect(
            (el, mountedAndLoaded) => {
                if (el && mountedAndLoaded) {
                    el.addEventListener("scroll", saveScroll);
                    observer.observe(el);
                    return () => {
                        observer.unobserve(el);
                        el.removeEventListener("scroll", saveScroll);
                    };
                }
            },
            () => [ref.el, this.state.mountedAndLoaded]
        );
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
