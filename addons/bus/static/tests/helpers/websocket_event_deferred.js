/* @odoo-module */

import { patchWebsocketWorkerWithCleanup } from "@bus/../tests/helpers/mock_websocket";

import { makeDeferred } from "@web/../tests/helpers/utils";
import { registerCleanup } from "@web/../tests/helpers/cleanup";
import { patch, unpatch } from "@web/core/utils/patch";

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
    const uuid = String(Date.now() + Math.random());
    const missingChannels = new Set(channels);
    const deferred = makeDeferred();
    function check({ crashOnFail = false } = {}) {
        const success = missingChannels.size === 0;
        if (!success && !crashOnFail) {
            return;
        }
        unpatch(worker, uuid);
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
    patch(worker, uuid, {
        async [operation === "add" ? "_addChannel" : "_deleteChannel"](client, channel) {
            await this._super(client, channel);
            missingChannels.delete(channel);
            check();
        },
    });
    return deferred;
}
