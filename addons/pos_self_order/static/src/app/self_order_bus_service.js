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
        bus_service.subscribe("ORDER_STATE_CHANGED", (payload) =>
            this.ws_changeOrderState(payload.access_token, payload.state)
        );
        bus_service.subscribe("ORDER_CHANGED", (payload) => this.ws_syncOrder(payload.order));
        bus_service.subscribe("STATUS", (payload) => {
            if (this.selfOrder.config.self_ordering_mode === "kiosk") {
                this.ws_status(payload);
            }
        });
        bus_service.subscribe("PAYMENT_STATUS", (payload) => {
            if (this.selfOrder.config.self_ordering_mode === "kiosk") {
                this.ws_paymentStatus(payload);
            }
        });
        bus_service.subscribe("PRODUCT_CHANGED", (payload) => this.ws_productChanged(payload));
    }

    ws_changeOrderState(access_token, state) {
        this.selfOrder.changeOrderState(access_token, state);
    }

    ws_syncOrder(order, state) {
        this.selfOrder.updateOrdersFromServer([order], [order.access_token]);
    }

    ws_paymentStatus(payload) {
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

    ws_status(payload) {
        if (payload.status === "closed") {
            this.selfOrder.pos_session = [];
            this.selfOrder.ordering = false;
        } else {
            // reload to get potential new settings
            // more easier than RPC for now
            window.location.reload();
        }
    }

    ws_productChanged(payload) {
        this.selfOrder.handleProductChanges(payload);
    }
}

export const SelfOrderBusService = {
    dependencies: SelfOrderBus.serviceDependencies,
    async start(env, deps) {
        return new SelfOrderBus(env, deps);
    },
};

registry.category("services").add("self_order_bus_service", SelfOrderBusService);
