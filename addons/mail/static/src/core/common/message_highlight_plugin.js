import { Thread } from "@mail/core/common/thread_model";
import { onWillDestroy, Plugin, signal, t, useConfig } from "@odoo/owl";

/** Duration in ms during which a message stays highlighted. */
export const HIGHLIGHT_DURATION = 1500;

/**
 * Highlights a message of the thread given in config, loading the messages
 * around it when needed. Components displaying the thread react to the
 * highlighted message, for instance by scrolling to it.
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
    /**
     * Whether the highlighted message is older than the messages that were
     * loaded when it was highlighted.
     */
    isOlderThanLoaded = signal(false, { type: t.boolean() });
    /** @type {number|null} */
    timeout = null;

    setup() {
        onWillDestroy(() => window.clearTimeout(this.timeout));
    }

    clear() {
        if (this.highlightedMessageId()) {
            window.clearTimeout(this.timeout);
            this.timeout = null;
            this.highlightedMessageId.set(null);
            this.isOlderThanLoaded.set(false);
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
        let isOlderThanLoaded = false;
        if (message.notIn(thread.messages)) {
            isOlderThanLoaded = message.id < thread.messages[0]?.id;
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
        this.isOlderThanLoaded.set(isOlderThanLoaded);
        this.highlightedMessageId.set(message.id);
        this.timeout = window.setTimeout(() => this.clear(), this.duration);
    }
}
