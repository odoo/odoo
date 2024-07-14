/** @odoo-module **/
import { reactive, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { useService } from "@web/core/utils/hooks";

const orderTrackingDisplayService = {
    dependencies: ["bus_service", "rpc"],
    async start(env, { bus_service, rpc }) {
        const orders = reactive(session.initial_data);
        bus_service.addChannel(`pos_tracking_display-${session.preparation_display.access_token}`);
        bus_service.subscribe("NEW_ORDERS", (newOrders) => {
            Object.assign(orders, newOrders);
        });
        bus_service.start();
        return orders;
    },
};

registry.category("services").add("order_tracking_display", orderTrackingDisplayService);
export function useOrderStatusDisplay() {
    return useState(useService("order_tracking_display"));
}
