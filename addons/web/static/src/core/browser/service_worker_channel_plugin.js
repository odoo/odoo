import { onWillDestroy, Plugin } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { services } from "@web/core/services";

// Shared with web/static/src/service_worker.js
const CHANNEL_NAME = "service_worker_channel";
const DELIVER = "service_worker_channel:deliver";
const READY = "service_worker_channel:ready";
const ACK = "service_worker_channel:ack";

/**
 * Receives the messages the service worker delivers to the pages, such as
 * what a click on a declarative push notification asks the page to do (see
 * the `deliver` step in web/static/src/service_worker.js).
 *
 * The service worker keeps a delivery until a page acknowledges it: a page
 * opened by the click gets it once it listens, even though it was still
 * loading when the message was first sent.
 */
export class ServiceWorkerChannelPlugin extends Plugin {
    /** @type {Map<string, Set<(message: any) => void>>} */
    handlers = new Map();
    /**
     * A delivery can reach a page twice: when it is sent, and again when the
     * page starts listening before it acknowledged it.
     *
     * @type {Set<string>}
     */
    handledIds = new Set();
    /** @type {BroadcastChannel|null} */
    broadcastChannel = null;

    setup() {
        this.onMessage = this.onMessage.bind(this);
        onWillDestroy(() => {
            this.broadcastChannel?.close();
            browser.navigator.serviceWorker?.removeEventListener("message", this.onMessage);
        });
    }

    /**
     * Call `handler` with each message delivered on `channel`, including the
     * ones delivered while this page was loading.
     *
     * @param {string} channel
     * @param {(message: any) => void} handler
     * @returns {() => void} stops listening
     */
    listen(channel, handler) {
        if (!browser.navigator.serviceWorker) {
            return () => {};
        }
        if (!this.broadcastChannel) {
            // Messages meant for every page are broadcast, the others are
            // posted to one page.
            this.broadcastChannel = new browser.BroadcastChannel(CHANNEL_NAME);
            this.broadcastChannel.addEventListener("message", this.onMessage);
            browser.navigator.serviceWorker.addEventListener("message", this.onMessage);
        }
        if (!this.handlers.has(channel)) {
            this.handlers.set(channel, new Set());
        }
        const handlers = this.handlers.get(channel);
        handlers.add(handler);
        if (handlers.size === 1) {
            this.postToWorker({ type: READY, channel });
        }
        return () => handlers.delete(handler);
    }

    /**
     * @param {MessageEvent} event
     */
    onMessage({ data }) {
        if (data?.type !== DELIVER || this.handledIds.has(data.id)) {
            return;
        }
        const handlers = this.handlers.get(data.channel);
        if (!handlers?.size) {
            // Not acknowledged: the worker keeps it for a page that listens.
            return;
        }
        this.handledIds.add(data.id);
        this.postToWorker({ type: ACK, id: data.id });
        for (const handler of handlers) {
            handler(data.message);
        }
    }

    /**
     * Post to the active worker rather than to the controller: a page loaded
     * with a hard reload has no controller.
     *
     * @param {Object} message
     */
    async postToWorker(message) {
        const registration = await browser.navigator.serviceWorker.ready;
        registration.active?.postMessage(message);
    }
}

services.add(ServiceWorkerChannelPlugin);
