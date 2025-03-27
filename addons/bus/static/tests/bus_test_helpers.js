import { after, expect, registerDebugInfo } from "@odoo/hoot";
import { Deferred } from "@odoo/hoot-mock";
import {
    MockServer,
    defineModels,
    mockService,
    patchWithCleanup,
    webModels,
} from "@web/../tests/web_test_helpers";
import { BusBus } from "./mock_server/mock_models/bus_bus";
import { IrWebSocket } from "./mock_server/mock_models/ir_websocket";
import { onWebsocketEvent } from "./mock_websocket";

import { busService } from "@bus/services/bus_service";
import { WEBSOCKET_CLOSE_CODES } from "@bus/workers/websocket_worker";
import { on } from "@odoo/hoot-dom";
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";

/**
 * @typedef {[
 *  env: import("@web/env").OdooEnv,
 *  notificationType: string,
 *  notificationPayload: any,
 *  options: ExpectedNotificationOptions,
 * ]} ExpectedNotification
 *
 * @typedef {{
 *  received?: boolean;
 * }} ExpectedNotificationOptions
 */

//-----------------------------------------------------------------------------
// Setup
//-----------------------------------------------------------------------------

patch(busService, {
    _onMessage(env, id, type, payload) {
        // Generic handlers (namely: debug info)
        if (type in busMessageHandlers) {
            busMessageHandlers[type](env, id, payload);
        } else {
            registerDebugInfo("bus message", { id, type, payload });
        }

        // Notifications
        if (!busNotifications.has(env)) {
            busNotifications.set(env, []);
            after(() => busNotifications.clear());
        }
        busNotifications.get(env).push({ id, type, payload });
    },
});

class LockedWebSocket extends WebSocket {
    constructor() {
        super(...arguments);

        this.addEventListener("open", (ev) => {
            ev.stopImmediatePropagation();

            this.dispatchEvent(new Event("error"));
            this.close(WEBSOCKET_CLOSE_CODES.ABNORMAL_CLOSURE);
        });
    }
}

/** @type {Record<string, (env: OdooEnv, id: string, payload: any) => any>} */
const busMessageHandlers = {};
/** @type {Map<OdooEnv, { id: number, type: string, payload: NotificationPayload }[]>} */
const busNotifications = new Map();

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

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/**
 * Useful to display debug information about bus events in tests.
 *
 * @param {string} type
 * @param {(env: OdooEnv, id: string, payload: any) => any} handler
 */
export function addBusMessageHandler(type, handler) {
    busMessageHandlers[type] = handler;
}

/**
 * Patches the bus service to add given event listeners immediatly when it starts.
 *
 * @param  {...[string, (event: CustomEvent) => any]} listeners
 */
export function addBusServiceListeners(...listeners) {
    mockService("bus_service", (env, dependencies) => {
        const busServiceInstance = busService.start(env, dependencies);
        for (const [type, handler] of listeners) {
            after(on(busServiceInstance, type, handler));
        }
        return busServiceInstance;
    });
}

export function defineBusModels() {
    return defineModels({ ...webModels, ...busModels });
}

/**
 * Returns a deferred that resolves when a websocket subscription is
 * done.
 *
 * @returns {Deferred<void>}
 */
export function waitUntilSubscribe() {
    const def = new Deferred();
    const timeout = setTimeout(() => handleResult(false), TIMEOUT);

    function handleResult(success) {
        clearTimeout(timeout);
        offWebsocketEvent();
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
    const offWebsocketEvent = onWebsocketEvent("subscribe", () => handleResult(true));
    return def;
}

/**
 * Returns a deferred that resolves when the given channel addition/deletion
 * occurs. Resolve immediately if the operation was already done.
 *
 * @param {string[]} channels
 * @param {object} [options={}]
 * @param {"add" | "delete"} [options.operation="add"]
 * @returns {Deferred<void>}
 */
export function waitForChannels(channels, { operation = "add" } = {}) {
    const { env } = MockServer;
    const def = new Deferred();
    let done = false;

    /**
     * @param {boolean} crashOnFail
     */
    function check(crashOnFail) {
        if (done) {
            return;
        }
        const userChannels = new Set(env["bus.bus"].channelsByUser[env.uid]);
        const success = channels.every((c) =>
            operation === "add" ? userChannels.has(c) : !userChannels.has(c)
        );
        if (!success && !crashOnFail) {
            return;
        }
        clearTimeout(failTimeout);
        offWebsocketEvent();
        const message = (pass, r) =>
            pass
                ? [r`Channel(s)`, channels, operation === "add" ? r`added` : r`deleted`]
                : [
                      r`Waited`,
                      TIMEOUT,
                      r`ms for`,
                      channels,
                      r`to be`,
                      operation === "add" ? r`added` : r`deleted`,
                  ];
        expect(success).toBe(true, { message });
        if (success) {
            def.resolve();
        } else {
            def.reject(new Error(message(false)));
        }
        done = true;
    }

    const failTimeout = setTimeout(() => check(true), TIMEOUT);
    after(() => check(true));
    const offWebsocketEvent = onWebsocketEvent("subscribe", () => check(false));
    check(false);
    return def;
}

/**
 * Wait for a notification to be received/not received. Returns
 * a deferred that resolves when the assertion is done.
 *
 * @param {ExpectedNotification} notification
 * @returns {Deferred<void>}
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
            expect(notifPayload).toEqual(payload, {
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
 * @returns {Promise<void[]>}
 */
export function waitNotifications(...expectedNotifications) {
    return Promise.all(expectedNotifications.map(_waitNotification));
}

/**
 * Lock the websocket connection until the returned function is called. Usefull
 * to simulate server being unavailable.
 */
export function lockWebsocketConnect() {
    return patchWithCleanup(window, { WebSocket: LockedWebSocket });
}

export const busModels = { BusBus, IrWebSocket };
