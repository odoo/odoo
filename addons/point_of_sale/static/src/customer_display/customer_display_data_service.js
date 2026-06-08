import { proxy } from "@odoo/owl";
import { getOnNotified } from "@point_of_sale/utils";
import { registry } from "@web/core/registry";
import { session } from "@web/session";

export const CustomerDisplayDataService = {
    dependencies: ["bus_service"],
    async start(env, services) {
        return this.setup(...arguments);
    },
    async setup(env, { bus_service }) {
        const data = proxy({});

        const currentTheme = new URLSearchParams(location.search).get("theme") || "light";

        const _processDisplayUpdate = (payload) => {
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

        new BroadcastChannel("UPDATE_CUSTOMER_DISPLAY").onmessage = (event) =>
            _processDisplayUpdate(event.data);
        getOnNotified(bus_service, session.access_token)(
            `UPDATE_CUSTOMER_DISPLAY-${session.device_uuid}`,
            _processDisplayUpdate
        );
        return data;
    },
};

registry.category("services").add("customer_display_data", CustomerDisplayDataService);
