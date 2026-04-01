import { reactive } from "@odoo/owl";
import { getOnNotified } from "@point_of_sale/utils";
import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { _t } from "@web/core/l10n/translation";

export const CustomerDisplayDataService = {
    dependencies: ["bus_service", "notification"],
    async start(env, { bus_service, notification }) {
        const data = reactive({});
        if (session.proxy_ip) {
            const intervalId = setInterval(async () => {
                try {
                    const response = await fetch(
                        `http://localhost:8069/hw_proxy/customer_facing_display`,
                        {
                            method: "POST",
                            headers: {
                                Accept: "application/json",
                                "Content-Type": "application/json",
                            },
                            body: JSON.stringify({
                                params: {
                                    action: "get",
                                },
                            }),
                        }
                    );
                    const payload = await response.json();
                    Object.assign(data, payload.result?.data || payload.result);
                } catch (error) {
                    notification.add(
                        _t(
                            "Make sure there is an IoT Box subscription associated with your Odoo database, then restart the IoT Box."
                        ),
                        {
                            title: _t("IoT Customer Display Error"),
                            type: "danger",
                        }
                    );
                    console.error("Error fetching data for the IoT customer display: %s", error);
                    clearInterval(intervalId);
                }
            }, 1000);
        } else {
            new BroadcastChannel("UPDATE_CUSTOMER_DISPLAY").onmessage = (event) => {
                Object.assign(data, event.data);
            };
            getOnNotified(bus_service, session.access_token)(
                `UPDATE_CUSTOMER_DISPLAY-${session.device_uuid}`,
                (payload) => {
                    Object.assign(data, payload);
                }
            );
        }
        return data;
    },
};

registry.category("services").add("customer_display_data", CustomerDisplayDataService);
