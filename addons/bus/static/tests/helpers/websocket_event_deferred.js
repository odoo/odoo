/* @odoo-module */

import { patchWebsocketWorkerWithCleanup } from "@bus/../tests/helpers/mock_websocket";

import { makeDeferred } from "@web/../tests/helpers/utils";

// should be enough to decide whether or not notifications/channel
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
    const successDeferred = makeDeferred();
    const failTimeout = setTimeout(() => {
        const failMessage = `Waited ${TIMEOUT}ms for ${channels.join(", ")} to be ${
            operation === "add" ? "added" : "deleted"
        }`;
        QUnit.assert.ok(false, failMessage);
        successDeferred.resolve();
    }, TIMEOUT);
    const channelsSeen = new Set();
    patchWebsocketWorkerWithCleanup({
        async [operation === "add" ? "_addChannel" : "_deleteChannel"](client, channel) {
            await this._super(client, channel);
            if (channels.includes(channel)) {
                channelsSeen.add(channel);
            }
            if (channelsSeen.size === channels.length) {
                QUnit.assert.ok(
                    true,
                    `Channel(s) ${channels.join(", ")} ${
                        operation === "add" ? "added" : "deleted"
                    }.`
                );
                successDeferred.resolve();
                clearTimeout(failTimeout);
            }
        },
    });
    return successDeferred;
}
