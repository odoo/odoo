import { after } from "@odoo/hoot";
import { Deferred, mockWorker } from "@odoo/hoot-mock";
import { MockServer } from "@web/../tests/web_test_helpers";

import { WebsocketWorker } from "@bus/workers/websocket_worker";
import { patch } from "@web/core/utils/patch";

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

function cleanupWebSocketCallbacks() {
    wsCallbacks?.clear();
    wsCallbacks = null;
}

function cleanupWekSocketWorker() {
    if (currentWebSocketWorker.connectTimeout) {
        clearTimeout(currentWebSocketWorker.connectTimeout);
    }

    currentWebSocketWorker.firstSubscribeDeferred = new Deferred();
    currentWebSocketWorker.websocket = null;
    currentWebSocketWorker = null;
}

function getWebSocketCallbacks() {
    if (!wsCallbacks) {
        wsCallbacks = new Map();

        after(cleanupWebSocketCallbacks);
    }

    return wsCallbacks;
}

/**
 * @param {SharedWorker | Worker} worker
 */
function onWorkerConnected(worker) {
    currentWebSocketWorker.registerClient(worker._messageChannel.port2);
}

function setupWebSocketWorker() {
    currentWebSocketWorker = new WebsocketWorker();

    mockWorker(onWorkerConnected);
}

/** @type {WebsocketWorker | null} */
let currentWebSocketWorker = null;
/** @type {Map<string, (data: any) => any> | null} */
let wsCallbacks = null;

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

export function getWebSocketWorker() {
    return currentWebSocketWorker;
}

/**
 * @param {string} eventName
 * @param {(data: any) => any} callback
 */
export function onWebsocketEvent(eventName, callback) {
    const callbacks = getWebSocketCallbacks();
    if (!callbacks.has(eventName)) {
        callbacks.set(eventName, new Set());
    }
    callbacks.get(eventName).add(callback);

    return function offWebsocketEvent() {
        callbacks.get(eventName).delete(callback);
    };
}

//-----------------------------------------------------------------------------
// Setup
//-----------------------------------------------------------------------------

patch(MockServer.prototype, {
    start() {
        setupWebSocketWorker();
        after(cleanupWekSocketWorker);

        return super.start(...arguments);
    },
});

patch(WebsocketWorker.prototype, {
    INITIAL_RECONNECT_DELAY: 0,
    RECONNECT_JITTER: 5,
    // `runAllTimers` advances time based on the longest registered timeout.
    // Some tests rely on the fragile assumption that time won’t advance too much.
    // Disable the interval until those tests are rewritten to be more robust.
    enableCheckInterval: false,

    _restartConnectionCheckInterval() {
        if (this.enableCheckInterval) {
            super._restartConnectionCheckInterval(...arguments);
        }
    },

    _sendToServer(message) {
        const { env } = MockServer;
        if (!env) {
            return;
        }

        if ("bus.bus" in env && "ir.websocket" in env) {
            if (message.event_name === "update_presence") {
                const { inactivity_period, im_status_ids_by_model } = message.data;
                env["ir.websocket"]._update_presence(inactivity_period, im_status_ids_by_model);
            } else if (message.event_name === "subscribe") {
                const { channels } = message.data;
                env["bus.bus"].channelsByUser[env.uid] = channels;
            }
        }

        // Custom callbacks
        for (const callback of wsCallbacks?.get(message.event_name) || []) {
            callback(message.data);
        }

        return super._sendToServer(message);
    },
});
