import { after, beforeEach } from "@odoo/hoot";
import { mockWorker } from "@odoo/hoot-mock";
import { MockServer } from "@web/../tests/web_test_helpers";

import { WebsocketWorker } from "@bus/workers/websocket_worker";
import { patch } from "@web/core/utils/patch";

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

const getWebSocketCallbacks = () => {
    if (!wsCallbacks) {
        wsCallbacks = new Map();
        after(() => {
            wsCallbacks?.clear();
            wsCallbacks = null;
        });
    }
    return wsCallbacks;
};

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

beforeEach(
    () => {
        currentWebSocketWorker = new WebsocketWorker();
        mockWorker((worker) => currentWebSocketWorker.registerClient(worker._messageChannel.port2));
        return () => {
            if (currentWebSocketWorker.connectTimeout) {
                clearTimeout(currentWebSocketWorker.connectTimeout);
            }
            currentWebSocketWorker.websocket = null;
            currentWebSocketWorker = null;
        };
    },
    { global: true }
);
patch(WebsocketWorker.prototype, {
    INITIAL_RECONNECT_DELAY: 0,
    RECONNECT_JITTER: 5,
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
