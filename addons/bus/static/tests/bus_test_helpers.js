import { busService } from "@bus/services/bus_service";

import { after, expect, registerDebugInfo } from "@odoo/hoot";
import { Deferred } from "@odoo/hoot-mock";
import {
    MockServer,
    defineModels,
    patchWithCleanup,
    webModels,
} from "@web/../tests/web_test_helpers";
import { BusBus } from "./mock_server/mock_models/bus_bus";
import { IrWebSocket } from "./mock_server/mock_models/ir_websocket";

import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import { WEBSOCKET_CLOSE_CODES } from "@bus/workers/websocket_worker";

patch(busService, {
    _onMessage(id, type, payload) {
        registerDebugInfo("bus:", id, type, payload);
    },
});

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

export function defineBusModels() {
    return defineModels({ ...webModels, ...busModels });
}

export const busModels = { BusBus, IrWebSocket };

//-----------------------------------------------------------------------------
// Setup
//-----------------------------------------------------------------------------

const viewsRegistry = registry.category("bus.view.archs");
viewsRegistry.category("activity").add(
    "default",
    /* xml */ `
        <activity><templates /></activity>
    `
);
viewsRegistry.category("form").add("default", /* xml */ `<form />`);
viewsRegistry.category("kanban").add("default", /* xml */ `<kanban><templates /></kanban>`);
viewsRegistry.category("list").add("default", /* xml */ `<list />`);
viewsRegistry.category("search").add("default", /* xml */ `<search />`);

viewsRegistry.category("form").add(
    "res.partner",
    /* xml */ `
    <form>
        <sheet>
            <field name="name" />
        </sheet>
        <chatter/>
    </form>`
);

// should be enough to decide whether or not notifications/channel
// subscriptions... are received.
const TIMEOUT = 500;

/**
 * @param {string} eventName
 * @param {Function} cb
 */
export function onWebsocketEvent(eventName, cb) {
    const callbacks = registry
        .category("mock_server_websocket_callbacks")
        .get(eventName, new Set());
    callbacks.add(cb);
    registry.category("mock_server_websocket_callbacks").add(eventName, callbacks, { force: true });
}

/**
 * @param {string} eventName
 * @param {Function} cb
 */
export function offWebsocketEvent(eventName, cb) {
    registry.category("mock_server_websocket_callbacks").get(eventName, new Set()).delete(cb);
}

/**
 * Returns a deferred that resolves when a websocket subscription is
 * done.
 *
 * @returns {import("@web/core/utils/concurrency").Deferred}
 */
export function waitUntilSubscribe() {
    const def = new Deferred();
    const timeout = setTimeout(() => handleResult(false), TIMEOUT);

    function handleResult(success) {
        clearTimeout(timeout);
        offWebsocketEvent("subscribe", onSubscribe);
        const message = success
            ? "Websocket subscription received."
            : "Websocket subscription not received.";
        expect(success).toBe(true, { message });
        if (success) {
            def.resolve();
        } else {
            def.reject(new Error(message));
        }
    }
    const onSubscribe = () => handleResult(true);
    onWebsocketEvent("subscribe", onSubscribe);
    return def;
}

/**
 * Returns a deferred that resolves when the given channel addition/deletion
 * occurs. Resolve immediately if the operation was already done.
 *
 * @param {string[]} channels
 * @param {object} [options={}]
 * @param {"add"|"delete"} [options.operation="add"]
 *
 * @returns {import("@web/core/utils/concurrency").Deferred} */
export function waitForChannels(channels, { operation = "add" } = {}) {
    const { env } = MockServer;
    const def = new Deferred();
    let done = false;

    function check({ crashOnFail = false } = {}) {
        const userChannels = new Set(env["bus.bus"].channelsByUser[env.uid]);
        const success = channels.every((c) =>
            operation === "add" ? userChannels.has(c) : !userChannels.has(c)
        );
        if (!success && !crashOnFail) {
            return;
        }
        clearTimeout(failTimeout);
        offWebsocketEvent("subscribe", check);
        const message = success
            ? `Channel(s) [${channels.join(", ")}] ${operation === "add" ? "added" : "deleted"}.`
            : `Waited ${TIMEOUT}ms for [${channels.join(", ")}] to be ${
                  operation === "add" ? "added" : "deleted"
              }`;
        expect(success).toBe(true, { message });
        if (success) {
            def.resolve();
        } else {
            def.reject(new Error(message));
        }
        done = true;
    }

    const failTimeout = setTimeout(() => check({ crashOnFail: true }), TIMEOUT);
    after(() => {
        if (!done) {
            check({ crashOnFail: true });
        }
    });
    onWebsocketEvent("subscribe", check);
    check();
    return def;
}

/**
 * @typedef {Object} ExpectedNotificationOptions
 * @property {boolean} [received=true]
 * @typedef {[env: import("@web/env").OdooEnv, notificationType: string, notificationPayload: any, options: ExpectedNotificationOptions]} ExpectedNotification
 */

/**
 * Wait for a notification to be received/not received. Returns
 * a deferred that resolves when the assertion is done.
 *
 * @param {ExpectedNotification} notification
 * @returns {import("@web/core/utils/concurrency").Deferred}
 */
function _waitNotification(notification) {
    const [env, type, payload, { received = true } = {}] = notification;
    const notificationDeferred = new Deferred();
    const failTimeout = setTimeout(() => {
        expect(!received).toBe(true, {
            message: `Notification of type "${type}" with payload ${payload} not received.`,
        });
        env.services["bus_service"].unsubscribe(type, callback);
        notificationDeferred.resolve();
    }, TIMEOUT);
    const callback = (notifPayload) => {
        if (payload === undefined || JSON.stringify(notifPayload) === JSON.stringify(payload)) {
            expect(received).toBe(true, {
                message: `Notification of type "${type}" with payload ${JSON.stringify(
                    notifPayload
                )} receveived.`,
            });

            notificationDeferred.resolve();
            clearTimeout(failTimeout);
            env.services["bus_service"].unsubscribe(type, callback);
        }
    };
    env.services["bus_service"].subscribe(type, callback);
    return notificationDeferred;
}

/**
 * Wait for the expected notifications to be received/not received. Returns
 * a deferred that resolves when the assertion is done.
 *
 * @param {ExpectedNotification[]} expectedNotifications
 * @returns {import("@web/core/utils/concurrency").Deferred}
 */
export function waitNotifications(...expectedNotifications) {
    return Promise.all(
        expectedNotifications.map((expectedNotification) => _waitNotification(expectedNotification))
    );
}

/**
 * Lock the bus service start process until the returned function is called.
 * This is useful in tests where an environment is mounted and the bus service
 * is started immediately. However, some tests need to wait in order to setup
 * their listeners.
 *
 * @returns {Function} A function that can be used to unlock the bus service
 * start process.
 */
export function lockBusServiceStart() {
    const unlockDeferred = new Deferred();
    patchWithCleanup(busService, {
        start() {
            const API = super.start(...arguments);
            patch(API, {
                async start() {
                    await unlockDeferred;
                    return super.start(...arguments);
                },
            });
            return API;
        },
    });
    return () => unlockDeferred.resolve();
}

/**
 *  Lock the websocket connection until the returned function is called. Usefull
 *  to simulate server being unavailable.
 *
 * @returns {Function} A function that can be used to unlock the websocket
 * connection.
 */
export function lockWebsocketConnect() {
    let locked = true;
    const ogSocket = window.WebSocket;
    patchWithCleanup(window, {
        WebSocket: function () {
            const ws = locked ? new EventTarget() : new ogSocket(...arguments);
            if (locked) {
                queueMicrotask(() => {
                    ws.dispatchEvent(new Event("error"));
                    ws.dispatchEvent(
                        new CloseEvent("close", { code: WEBSOCKET_CLOSE_CODES.ABNORMAL_CLOSURE })
                    );
                });
            }
            return ws;
        },
    });
    return () => (locked = false);
}
