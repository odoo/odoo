/* @odoo-module */

import { patchWebsocketWorkerWithCleanup } from "@bus/../tests/helpers/mock_websocket";

import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import { registerCleanup } from "@web/../tests/helpers/cleanup";
import { makeDeferred } from "@web/../tests/helpers/utils";

// should be enough to decide whether or not notifications/channel
// subscriptions... are received.
const TIMEOUT = 2000;
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
    const subscribeDeferred = makeDeferred();
    const failTimeout = setTimeout(() => {
        const errMsg = `Subscription to ${JSON.stringify(requiredChannels)} not received.`;
        subscribeDeferred.reject(new Error(errMsg));
        QUnit.assert.ok(false, errMsg);
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
                QUnit.assert.ok(
                    true,
                    `Subscription to ${JSON.stringify(requiredChannels)} received.`
                );
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
    const deferred = makeDeferred();
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
        QUnit.assert.ok(success, msg);
        if (success) {
            deferred.resolve();
        } else {
            deferred.reject(new Error(msg));
        }
    }
    const failTimeout = setTimeout(() => check({ crashOnFail: true }), TIMEOUT);
    registerCleanup(() => {
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
    const notificationDeferred = makeDeferred();
    const failTimeout = setTimeout(() => {
        QUnit.assert.ok(
            !received,
            `Notification of type "${type}" with payload ${payload} not received.`
        );
        env.services["bus_service"].removeEventListener("notification", callback);
        notificationDeferred.resolve();
    }, TIMEOUT);
    const callback = ({ detail: notifications }) => {
        for (const notification of notifications) {
            if (notification.type !== type) {
                continue;
            }
            if (
                payload === undefined ||
                JSON.stringify(notification.payload) === JSON.stringify(payload)
            ) {
                QUnit.assert.ok(
                    received,
                    `Notification of type "${type}" with payload ${JSON.stringify(
                        notification.payload
                    )} receveived.`
                );
                notificationDeferred.resolve();
                clearTimeout(failTimeout);
                env.services["bus_service"].removeEventListener("notification", callback);
            }
        }
    };
    env.services["bus_service"].addEventListener("notification", callback);
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
 * Returns a deferred that resolves when an event matching the given type is
 * received from the bus service.
 *
 * @typedef {"connect"|"disconnect"|"reconnect"|"reconnecting"|"notification"} EventType
 * @param {import("@web/env").OdooEnv} env
 * @param {EventType} eventType
 * @param {object} [options={}]
 * @param {boolean} [options.received=true]
 */
export function waitForBusEvent(env, eventType, { received = true } = {}) {
    const eventReceivedDeferred = makeDeferred();
    const failTimeout = setTimeout(() => {
        env.services["bus_service"].removeEventListener(eventType, callback);
        QUnit.assert.ok(
            !received,
            received
                ? `Waited ${TIMEOUT}ms for ${eventType} event.`
                : `Event of type "${eventType}" not received.`
        );
        eventReceivedDeferred.resolve();
    }, TIMEOUT);
    const callback = () => {
        env.services["bus_service"].removeEventListener(eventType, callback);
        QUnit.assert.ok(received, `Event of type "${eventType}" received.`);
        eventReceivedDeferred.resolve();
        clearTimeout(failTimeout);
    };
    env.services["bus_service"].addEventListener(eventType, callback);
    return eventReceivedDeferred;
}

/**
 * Returns a deferred that resolves when an event matching the given type is
 * received by the websocket worker.
 *
 * @param {import("@web/env").OdooEnv} env
 * @param {import("@bus/workers/websocket_worker").WorkerAction} targetAction
 * @param {object} [options={}]
 * @param {boolean} [options.received=true]
 */
export function waitForWorkerEvent(targetAction) {
    const eventReiceivedDeferred = makeDeferred();
    const failTimeout = setTimeout(() => {
        unpatch();
        QUnit.assert.ok(false, `Waited ${TIMEOUT}ms for ${targetAction} to be received.`);
        eventReiceivedDeferred.resolve();
    }, TIMEOUT);
    const worker = patchWebsocketWorkerWithCleanup();
    const unpatch = patch(worker, {
        _onClientMessage(_, { action }) {
            super._onClientMessage(...arguments);
            if (targetAction === action) {
                unpatch();
                QUnit.assert.ok(true, `Action "${action}" received.`);
                eventReiceivedDeferred.resolve();
                clearTimeout(failTimeout);
            }
        },
    });
    registerCleanup(unpatch);
    return eventReiceivedDeferred;
}
