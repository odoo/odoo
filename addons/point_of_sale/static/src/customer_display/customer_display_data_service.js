import { reactive } from "@odoo/owl";
import { deduceUrl, getOnNotified } from "@point_of_sale/utils";
import { registry } from "@web/core/registry";
import { session } from "@web/session";

export const CustomerDisplayDataService = {
    dependencies: ["bus_service"],
    async start(env, { bus_service }) {
        const data = reactive({});
        if (session.type === "local") {
            new BroadcastChannel("UPDATE_CUSTOMER_DISPLAY").onmessage = (event) => {
                Object.assign(data, event.data);
            };
        }
        if (session.type === "remote") {
            getOnNotified(bus_service, session.access_token)(
                "UPDATE_CUSTOMER_DISPLAY",
                (payload) => {
                    Object.assign(data, payload);
                }
            );
        }
        if (session.type === "proxy") {
            setInterval(async () => {
                const response = await fetch(
                    `${deduceUrl(session.proxy_ip)}/hw_proxy/customer_facing_display`,
                    {
                        method: "POST",
                        headers: {
                            Accept: "application/json",
                            "Content-Type": "application/json",
                        },
                        body: JSON.stringify({ params: { action: "get" } }),
                    }
                );
                const payload = await response.json();
                Object.assign(data, payload.result.data);
            }, 1000);
        }
        return data;
    },
};

registry.category("services").add("customer_display_data", CustomerDisplayDataService);
