/** @odoo-module **/

import { defineModels, webModels } from "@web/../tests/web_test_helpers";
import { registry } from "@web/core/registry";
import { BusBus } from "./mock_server/mock_models/bus_bus";
import { IrWebSocket } from "./mock_server/mock_models/ir_websocket";
import { Deferred } from "@odoo/hoot-mock";
import { expect } from "@odoo/hoot";

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
        <div class="oe_chatter">
            <field name="message_follower_ids" />
            <field name="message_ids" />
        </div>
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
        expect(false).toBeTruthy({ message: errMsg });
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
                expect(true).toBeTruthy({
                    message: `Subscription to ${JSON.stringify(requiredChannels)} received.`,
                });
                clearTimeout(failTimeout);
            }
        },
        { force: true }
    );
    return subscribeDeferred;
}
