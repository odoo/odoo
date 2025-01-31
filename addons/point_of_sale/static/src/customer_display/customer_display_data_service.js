import { reactive } from "@odoo/owl";
import { getOnNotified } from "@point_of_sale/utils";
import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { _t } from "@web/core/l10n/translation";
import { DeviceController } from "@iot/device_controller";

export const CustomerDisplayDataService = {
    dependencies: ["bus_service", "notification", "iot_longpolling"],
    async start(env, { bus_service, notification, iot_longpolling }) {
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
            const iotDisplay = new DeviceController(iot_longpolling, {
                iot_ip: session.proxy_ip,
                identifier: "HDMI-1",
            });
            const intervalId = setInterval(async () => {
                iotDisplay.addListener((response) => Object.assign(data, response.result));
                try {
                    iotDisplay.action({ action: "get_customer_display_data" });
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
                    iotDisplay.removeListener();
                    clearInterval(intervalId);
                }
            }, 1000);
        }
        return data;
    },
};

registry.category("services").add("customer_display_data", CustomerDisplayDataService);
