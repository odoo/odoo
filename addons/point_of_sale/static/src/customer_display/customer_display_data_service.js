import { reactive } from "@odoo/owl";
import { getOnNotified } from "@point_of_sale/utils";
import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";

// Tells the PoS we are listening, so that it only pushes updates to the server
// while a display is actually open. Must stay below the PoS side timeout.
const ALIVE_PING_INTERVAL = 15000;

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
            // We start blank on every load: as long as nothing was received, ask
            // the PoS for the current order rather than waiting for its next
            // change. A lost answer is simply asked again on the next ping.
            let hasData = false;
            const receive = (payload) => {
                hasData = true;
                Object.assign(data, payload);
            };
            // A BroadcastChannel message means the PoS runs in this very browser
            // and reaches us for free, so it never has to go through the server.
            let servedByBroadcast = false;
            let aliveIntervalId;
            new BroadcastChannel("UPDATE_CUSTOMER_DISPLAY").onmessage = (event) => {
                servedByBroadcast = true;
                clearInterval(aliveIntervalId);
                receive(event.data);
            };
            getOnNotified(bus_service, session.access_token)(
                `UPDATE_CUSTOMER_DISPLAY-${session.device_uuid}`,
                receive
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
        }
        return data;
    },
};

registry.category("services").add("customer_display_data", CustomerDisplayDataService);
