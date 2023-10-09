/* @odoo-module */

import { patchWebsocketWorkerWithCleanup } from "@bus/../tests/helpers/mock_websocket";

import { makeDeferred } from "@web/../tests/helpers/utils";
import { registry } from "@web/core/registry";

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
        subscribeDeferred.reject(new Error(`Waited 1s for ${requiredChannels} subscription`));
        console.error(`Waited 1s for ${requiredChannels} subscription`);
    }, 1000);
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
                clearTimeout(failTimeout);
            }
        },
        { force: true }
    );
    return subscribeDeferred;
}

/**
 * Returns a deferred that resolves when a channel addition is notified to the
 * websocket worker.
 *
 * @param {string} targetChannel
 * @returns {import("@web/core/utils/concurrency").Deferred}
 */
export function waitUntilChannelAdded(targetChannel) {
    const channelAddedDeferred = makeDeferred();
    const failTimeout = setTimeout(() => {
        channelAddedDeferred.reject(new Error(`Waited 1s for ${targetChannel} to be added`));
        console.error(`Waited 1s for ${targetChannel} to be added`);
    }, 1000);
    patchWebsocketWorkerWithCleanup({
        async _addChannel(client, channel) {
            await super._addChannel(client, channel);
            if (channel === targetChannel) {
                channelAddedDeferred.resolve();
                clearTimeout(failTimeout);
            }
        },
    });
    return channelAddedDeferred;
}

/**
 * Returns a deferred that resolves when a channel deletion is notified to the
 * websocket worker.
 *
 * @param {string} targetChannel
 * @returns {import("@web/core/utils/concurrency").Deferred}
 */
export function waitUntilChannelDeleted(targetChannel) {
    const channelDeletedDeferred = makeDeferred();
    const failTimeout = setTimeout(() => {
        channelDeletedDeferred.reject(new Error(`Waited 1s for ${targetChannel} to be deleted`));
        console.error(`Waited 1s for ${targetChannel} to be deleted`);
    }, 1000);
    patchWebsocketWorkerWithCleanup({
        async _deleteChannel(client, channel) {
            await super._deleteChannel(client, channel);
            if (channel === targetChannel) {
                channelDeletedDeferred.resolve();
                clearTimeout(failTimeout);
            }
        },
    });
    return channelDeletedDeferred;
}
