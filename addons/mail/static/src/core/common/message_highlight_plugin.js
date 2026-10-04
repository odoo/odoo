import { Thread } from "@mail/core/common/thread_model";
import { onWillDestroy, Plugin, signal, t, useConfig } from "@odoo/owl";

/** Duration in ms during which a message stays highlighted. */
export const HIGHLIGHT_DURATION = 1500;

/**
 * Highlights a message of the thread given in config, loading the messages
 * around it when needed, and scrolls to it.
 *
 * Config:
 * - `thread`: function returning the thread whose messages are highlighted.
 * - `messageFetchRouteParams` (optional): function returning the route
 *   params used to load the messages around the highlighted message.
 */
export class MessageHighlightPlugin extends Plugin {
    duration = HIGHLIGHT_DURATION;
    thread = useConfig("thread", t.function([], t.instanceOf(Thread).optional()));
    messageFetchRouteParams = useConfig(
        "messageFetchRouteParams",
        t.function([], t.object()).optional()
    );
    highlightedMessageId = signal(null, { type: t.or([t.number(), t.literal(null)]) });
    /** @type {number|null} */
    timeout = null;
    /**
     * Promise during highlight startup, i.e. highlight is initiated but isn't scrolling yet
     * Useful to set correct starting condition to initiate scroll to highlight, like scroll to bottom.
     *
     * @type {Promise<void>|null}
     */
    startupPromise = null;
    /** @type {(() => void)|null} */
    resolveStartup = null;
    /** @type {Promise<void>|null} Promise during scrolling to highlight */
    scrollPromise = null;
    /** @type {(() => void)|null} */
    resolveScroll = null;

    setup() {
        onWillDestroy(() => window.clearTimeout(this.timeout));
    }

    clear() {
        if (this.highlightedMessageId()) {
            window.clearTimeout(this.timeout);
            this.timeout = null;
            this.highlightedMessageId.set(null);
        }
    }

    /**
     * @param {import("models").Message} message
     */
    async highlightMessage(message) {
        const thread = this.thread();
        if (!thread) {
            return;
        }
        let messageScrollDirection;
        if (message.notIn(thread.messages)) {
            messageScrollDirection = message.id < thread.messages[0]?.id ? "top" : "bottom";
            await thread.loadAround({
                messageId: message.id,
                routeParams: this.messageFetchRouteParams ? this.messageFetchRouteParams() : {},
            });
        }
        const lastHighlightedMessageId = this.highlightedMessageId();
        this.clear();
        if (lastHighlightedMessageId === message.id) {
            // Give some time for the state to update.
            await new Promise(setTimeout);
        }
        thread.scrollTop = messageScrollDirection === "top" ? "bottom" : undefined;
        if (thread.scrollTop === "bottom") {
            this.startupPromise = new Promise((resolve) => (this.resolveStartup = resolve));
            await this.startupPromise;
            this.startupPromise = null;
            this.resolveStartup = null;
        }
        this.highlightedMessageId.set(message.id);
        this.timeout = window.setTimeout(() => this.clear(), this.duration);
    }

    /**
     * Scroll the element into view and expose a promise that will resolved
     * once the scroll is done.
     *
     * @param {Element} el
     */
    scrollTo(el) {
        this.resolveScroll?.();
        const { promise: scrollPromise, resolve: resolveScroll } = Promise.withResolvers();
        this.scrollPromise = scrollPromise;
        this.resolveScroll = resolveScroll;
        if ("onscrollend" in window) {
            document.addEventListener("scrollend", resolveScroll, {
                capture: true,
                once: true,
            });
        } else {
            // To remove when safari will support the "scrollend" event.
            setTimeout(resolveScroll, 250);
        }
        el.scrollIntoView({ behavior: "smooth", block: "center" });
        return scrollPromise;
    }
}
