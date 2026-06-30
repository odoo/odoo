import { after, expect, registerDebugInfo } from "@odoo/hoot";
import { Deferred } from "@odoo/hoot-mock";
import {
    MockServer,
    asyncStep,
    defineModels,
    getMockEnv,
    getService,
    mockService,
    patchWithCleanup,
    webModels,
} from "@web/../tests/web_test_helpers";
import { BusBus } from "./mock_server/mock_models/bus_bus";
import { IrWebSocket } from "./mock_server/mock_models/ir_websocket";
import { getWebSocketWorker, onWebsocketEvent } from "./mock_websocket";

import { busService } from "@bus/services/bus_service";
import { WEBSOCKET_CLOSE_CODES } from "@bus/workers/websocket_worker";
import { on, runAllTimers, waitUntil } from "@odoo/hoot-dom";
import { registry } from "@web/core/registry";
import { deepEqual } from "@web/core/utils/objects";
import { patch } from "@web/core/utils/patch";

/**
 * @typedef {[
 *  env?: OdooEnv,
 *  type: string,
 *  payload: NotificationPayload,
 *  options?: ExpectedNotificationOptions,
 * ]} ExpectedNotification
 *
 * @typedef {{
 *  received?: boolean;
 * }} ExpectedNotificationOptions
 *
 * @typedef {Record<string, any>} NotificationPayload
 *
 * @typedef {import("@web/env").OdooEnv} OdooEnv
 * @typedef {import("@bus/workers/websocket_worker").WorkerAction} WorkerAction
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

/**
 * @param {ExpectedNotification} notification
 * @param {boolean} [crashOnFail]
 */
const expectNotification = ([env, type, payload, options], crashOnFail) => {
    if (typeof env === "string") {
        [env, type, payload, options] = [getMockEnv(), env, type, payload];
    }
    const shouldHaveReceived = Boolean(options?.received ?? true);
    const envNotifications = busNotifications.get(env) || [];
    const hasPayload = payload !== null && payload !== undefined;
    const found = envNotifications.find(
        (n) => n.type === type && (!hasPayload || matchPayload(n.payload, payload))
    );
    const message = (pass) =>
        `Notification of type ${type} ${payload ? `with payload ${payload} ` : ""}${
            pass && shouldHaveReceived ? "" : "not "
        }received.`;
    if (found) {
        envNotifications.splice(envNotifications.indexOf(found), 1);
        expect(payload).toEqual(payload, { message });
    } else if (!shouldHaveReceived) {
        expect(shouldHaveReceived).toBe(false, { message });
    } else {
        if (crashOnFail) {
            throw new Error(message(false, String.raw).join(" "));
        }
        return false;
    }
    return true;
};

/**
 * @param {NotificationPayload} payload
 * @param {NotificationPayload | ((payload: NotificationPayload) => boolean)} matcher
 */
const matchPayload = (payload, matcher) =>
    typeof matcher === "function" ? matcher(payload) : deepEqual(payload, matcher);

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
const TIMEOUT = 2000;

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
 * @returns {Promise<void>}
 */
export async function waitForChannels(channels, { operation = "add" } = {}) {
    const { env } = MockServer;
    const def = new Deferred();
    let done = false;
    let failTimeout;

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
        const message = (pass) =>
            pass
                ? `Channel(s) ${channels} ${operation === "add" ? `added` : `deleted`}`
                : `Waited ${TIMEOUT}ms for ${channels} to be ${
                      operation === "add" ? `added` : `deleted`
                  }`;
        expect(success).toBe(true, { message });
        if (success) {
            def.resolve();
        } else {
            def.reject(new Error(message(false)));
        }
        done = true;
    }

    after(() => check(true));
    const offWebsocketEvent = onWebsocketEvent("subscribe", () => check(false));

    await runAllTimers();

    failTimeout = setTimeout(() => check(true), TIMEOUT);
    check(false);

    return def;
}

/**
 * Wait for the expected notifications to be received/not received. Returns
 * a deferred that resolves when the assertion is done.
 *
 * @param {ExpectedNotification[]} expectedNotifications
 * @returns {Promise<void>}
 */
export async function waitNotifications(...expectedNotifications) {
    const remaining = new Set(expectedNotifications);

    await waitUntil(
        () => {
            for (const notification of remaining) {
                if (expectNotification(notification, false)) {
                    remaining.delete(notification);
                }
            }
            return remaining.size === 0;
        },
        { timeout: TIMEOUT }
    )
        .then(() => busNotifications.clear())
        .catch(() => {
            for (const notification of remaining) {
                expectNotification(notification, true);
            }
        });
}

/**
 * Registers an asynchronous step on actions received by the websocket worker that
 * match the given list of target actions.
 *
 * @param {WorkerAction[]} targetActions
 */
export function stepWorkerActions(targetActions) {
    patchWithCleanup(getWebSocketWorker(), {
        _onClientMessage(_, { action }) {
            if (targetActions.includes(action)) {
                asyncStep(action);
            }
            return super._onClientMessage(...arguments);
        },
    });
}

/**
 * Lock the websocket connection until the returned function is called. Useful
 * to simulate server being unavailable.
 */
export function lockWebsocketConnect() {
    return patchWithCleanup(window, { WebSocket: LockedWebSocket });
}

/**
 * @param {OdooEnv} [env]
 */
export async function startBusService(env) {
    const busService = env ? env.services.bus_service : getService("bus_service");
    busService.start();
    await runAllTimers();
}

export const busModels = { BusBus, IrWebSocket };
