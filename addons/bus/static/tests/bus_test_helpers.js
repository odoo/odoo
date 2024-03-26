/** @odoo-module **/

import { defineModels, webModels } from "@web/../tests/web_test_helpers";
import { registry } from "@web/core/registry";
import { BusBus } from "./mock_server/mock_models/bus_bus";
import { IrWebSocket } from "./mock_server/mock_models/ir_websocket";
import { Deferred } from "@odoo/hoot-mock";
import { after, expect } from "@odoo/hoot";
import { patch } from "@web/core/utils/patch";
import { patchWebsocketWorkerWithCleanup } from "./mock_websocket";

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
viewsRegistry.category("list").add("default", /* xml */ `<tree />`);
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
const callbackRegistry = registry.category("mock_server_websocket_callbacks");

/**
 * Returns a deferred that resolves when a websocket subscription is
 * done. If channels are provided, the deferred will only resolve when
 * we subscribe to all of them.
 *
 * @param {...string} [requiredChannels]
 * @returns {import("@web/core/utils/concurrency").Deferred}
 */
export function waitUntilSubscribe(...requiredChannels) {
    const subscribeDeferred = new Deferred();
    const failTimeout = setTimeout(() => {
        const errMsg = `Subscription to ${JSON.stringify(requiredChannels)} not received.`;
        subscribeDeferred.reject(new Error(errMsg));
        expect(false).toBe(true, { message: errMsg });
    }, TIMEOUT);
    const lastCallback = callbackRegistry.get("subscribe", () => {});
    callbackRegistry.add(
        "subscribe",
        (data) => {
            const { channels } = data;
            lastCallback(data);
            const allChannelsSubscribed = requiredChannels.every((channel) =>
                channels.includes(channel)
            );
            if (allChannelsSubscribed) {
                subscribeDeferred.resolve();
                expect(true).toBe(true, {
                    message: `Subscription to ${JSON.stringify(requiredChannels)} received.`,
                });
                clearTimeout(failTimeout);
            }
        },
        { force: true }
    );
    return subscribeDeferred;
}

/**
 * Returns a deferred that resolves when the given channel(s) addition/deletion
 * is notified to the websocket worker.
 *
 * @param {string[]} channels
 * @param {object} [options={}]
 * @param {"add"|"delete"} [options.operation="add"]
 *
 * @returns {import("@web/core/utils/concurrency").Deferred} */
export function waitForChannels(channels, { operation = "add" } = {}) {
    const missingChannels = new Set(channels);
    const deferred = new Deferred();
    function check({ crashOnFail = false } = {}) {
        const success = missingChannels.size === 0;
        if (!success && !crashOnFail) {
            return;
        }
        unpatch();
        clearTimeout(failTimeout);
        const msg = success
            ? `Channel(s) [${channels.join(", ")}] ${operation === "add" ? "added" : "deleted"}.`
            : `Waited ${TIMEOUT}ms for [${channels.join(", ")}] to be ${
                  operation === "add" ? "added" : "deleted"
              }`;
        expect(success).toBe(true, { message: msg });
        if (success) {
            deferred.resolve();
        } else {
            deferred.reject(new Error(msg));
        }
    }
    const failTimeout = setTimeout(() => check({ crashOnFail: true }), TIMEOUT);
    after(() => {
        if (missingChannels.length > 0) {
            check({ crashOnFail: true });
        }
    });
    const worker = patchWebsocketWorkerWithCleanup();
    const workerMethod = operation === "add" ? "_addChannel" : "_deleteChannel";
    const unpatch = patch(worker, {
        async [workerMethod](client, channel) {
            await super[workerMethod](client, channel);
            missingChannels.delete(channel);
            check();
        },
    });
    return deferred;
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
