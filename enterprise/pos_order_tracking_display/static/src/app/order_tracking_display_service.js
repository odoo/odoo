import { reactive, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { useService } from "@web/core/utils/hooks";
import { getOnNotified } from "@point_of_sale/utils";

const orderTrackingDisplayService = {
    dependencies: ["bus_service"],
    async start(env, { bus_service }) {
        const orders = reactive(session.initial_data);
        const onNotified = getOnNotified(bus_service, session.preparation_display.access_token);
        onNotified("NEW_ORDERS", (newOrders) => {
            Object.assign(orders, newOrders);
        });
        return orders;
    },
};

registry.category("services").add("order_tracking_display", orderTrackingDisplayService);
export function useOrderStatusDisplay() {
    return useState(useService("order_tracking_display"));
}
