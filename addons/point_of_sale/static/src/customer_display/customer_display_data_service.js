import { reactive } from "@odoo/owl";
import { getOnNotified } from "@point_of_sale/utils";
import { registry } from "@web/core/registry";
import { session } from "@web/session";

export const CustomerDisplayDataService = {
    dependencies: ["bus_service"],
    async start(env, services) {
        return this.setup(...arguments);
    },
    async setup(env, { bus_service }) {
        const data = reactive({});
        new BroadcastChannel("UPDATE_CUSTOMER_DISPLAY").onmessage = (event) => {
            Object.assign(data, event.data);
        };
        getOnNotified(bus_service, session.access_token)(
            `UPDATE_CUSTOMER_DISPLAY-${session.device_uuid}`,
            (payload) => {
                Object.assign(data, payload);
            }
        );
        return data;
    },
};

registry.category("services").add("customer_display_data", CustomerDisplayDataService);
