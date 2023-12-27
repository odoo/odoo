/* @odoo-module */

import { patchWebsocketWorkerWithCleanup } from "@bus/../tests/helpers/mock_websocket";

import { makeDeferred } from "@web/../tests/helpers/utils";

// Should be enough to decide whether or not notifications/channel
// subscriptions... are received.
const TIMEOUT = 500;

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
    const channelsSeen = new Set();
    const successDeferred = makeDeferred();
    function check({ crashOnFail = false } = {}) {
        const success = channelsSeen.size === channels.length;
        if (!success && !crashOnFail) {
            return;
        }
        clearTimeout(failTimeout);
        const msg = success
            ? `Channel(s) [${channels.join(", ")}] ${operation === "add" ? "added" : "deleted"}.`
            : `Waited ${TIMEOUT}ms for ${channels.join(", ")} to be ${
                  operation === "add" ? "added" : "deleted"
              }`;
        QUnit.assert.ok(success, msg);
        if (success) {
            successDeferred.resolve();
        } else {
            successDeferred.reject(new Error(msg));
        }
    }
    const failTimeout = setTimeout(() => check({ crashOnFail: true }), TIMEOUT);
    patchWebsocketWorkerWithCleanup({
        async [operation === "add" ? "_addChannel" : "_deleteChannel"](client, channel) {
            await this._super(client, channel);
            if (channels.includes(channel)) {
                channelsSeen.add(channel);
            }
            check();
        },
    });
    return successDeferred;
}
