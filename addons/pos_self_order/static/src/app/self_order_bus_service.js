/** @odoo-module */

import { registry } from "@web/core/registry";
import { effect } from "@web/core/utils/reactive";
import { batched } from "@web/core/utils/timing";

export class SelfOrderBus {
    static serviceDependencies = ["self_order", "orm", "bus_service"];

    constructor(...args) {
        this.setup(...args);
    }

    setup(env, { self_order, orm, bus_service }) {
        this.selfOrder = self_order;
        this.orm = orm;
        this.bus = bus_service;

        effect(
            batched((orders) => {
                for (const order of orders) {
                    if (order.access_token) {
                        this.bus.addChannel(`self_order-${order.access_token}`);
                    }
                }
            }),
            [this.selfOrder.orders]
        );

        bus_service.addChannel(`pos_config-${this.selfOrder.access_token}`);
        bus_service.addEventListener("notification", ({ detail }) => {
            for (const message of detail) {
                this.dispatch(message);
            }
        });
    }

    dispatch(message) {
        const mode = this.selfOrder.config.self_ordering_mode;
        if (message.type === "ORDER_STATE_CHANGED") {
            this.ws_changeOrderState(message.payload.access_token, message.payload.state);
        } else if (message.type === "ORDER_CHANGED") {
            this.ws_syncOrder(message.payload.order);
        } else if (message.type === "STATUS" && mode === "kiosk") {
            this.ws_status(message);
        } else if (message.type === "PAYMENT_STATUS" && mode === "kiosk") {
            this.ws_paymentStatus(message);
        } else if (message.type === "PRODUCT_CHANGED") {
            this.ws_productChanged(message);
        }
    }

    ws_changeOrderState(access_token, state) {
        this.selfOrder.changeOrderState(access_token, state);
    }

    ws_syncOrder(order, state) {
        this.selfOrder.updateOrdersFromServer([order], [order.access_token]);
    }

    ws_paymentStatus(message) {
        const payload = message.payload;

        if (payload.payment_result === "Success") {
            this.selfOrder.updateOrderFromServer(payload.order);
            this.selfOrder.router.navigate("confirmation", {
                orderAccessToken: payload.order.access_token,
                screenMode: "order",
            });
        } else {
            this.selfOrder.paymentError = true;
        }
    }

    ws_status(message) {
        const payload = message.payload;

        if (payload.status === "closed") {
            this.selfOrder.pos_session = [];
            this.selfOrder.ordering = false;
        } else {
            // reload to get potential new settings
            // more easier than RPC for now
            window.location.reload();
        }
    }

    ws_productChanged(message) {
        this.selfOrder.handleProductChanges(message.payload);
    }
}

export const SelfOrderBusService = {
    dependencies: SelfOrderBus.serviceDependencies,
    async start(env, deps) {
        return new SelfOrderBus(env, deps);
    },
};

registry.category("services").add("self_order_bus_service", SelfOrderBusService);
