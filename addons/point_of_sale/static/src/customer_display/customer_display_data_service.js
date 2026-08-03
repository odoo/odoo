import { proxy } from "@odoo/owl";
import { getOnNotified } from "@point_of_sale/utils";
import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { rpc } from "@web/core/network/rpc";

// Tells the PoS we are listening, so that it only pushes updates to the server
// while a display is actually open. Must stay below the PoS side timeout.
const ALIVE_PING_INTERVAL = 60000;

export const CustomerDisplayDataService = {
    dependencies: ["bus_service"],
    async start(env, services) {
        return this.setup(...arguments);
    },
    async setup(env, { bus_service }) {
        const data = proxy({});

        const currentTheme = new URLSearchParams(location.search).get("theme") || "light";

        // We start blank on every load: as long as nothing was received, ask the
        // PoS for the current order rather than waiting for its next change. A
        // lost answer is simply asked again on the next ping.
        let hasData = false;
        // A BroadcastChannel message means the PoS runs in this very browser and
        // reaches us for free, so it never has to go through the server.
        let servedByBroadcast = false;
        let aliveIntervalId;

        const _processDisplayUpdate = (payload) => {
            hasData = true;
            const { displayTheme: posTheme } = payload;
            if (posTheme && currentTheme !== posTheme) {
                const searchParams = new URLSearchParams(location.search);
                searchParams.set("theme", posTheme);
                // Reload page to apply the new theme
                location.search = searchParams.toString();
                return;
            }
            Object.assign(data, payload);
        };

        new BroadcastChannel("UPDATE_CUSTOMER_DISPLAY").onmessage = (event) => {
            servedByBroadcast = true;
            clearInterval(aliveIntervalId);
            _processDisplayUpdate(event.data);
        };
        getOnNotified(bus_service, session.access_token)(
            `UPDATE_CUSTOMER_DISPLAY-${session.device_uuid}`,
            _processDisplayUpdate
        );

        const notifyAlive = () => {
            if (servedByBroadcast) {
                return;
            }
            rpc(
                `/pos_customer_display/${session.config_id}/${session.device_uuid}/alive`,
                { access_token: session.access_token, needs_data: !hasData },
                { silent: true }
            ).catch(() => {
                // Losing a ping is not worth bothering the customer with, the
                // next one will pair us back with the PoS.
            });
        };
        notifyAlive();
        aliveIntervalId = setInterval(notifyAlive, ALIVE_PING_INTERVAL);

        return data;
    },
};

registry.category("services").add("customer_display_data", CustomerDisplayDataService);
