/** @odoo-module */

import { registry } from "@web/core/registry";
import { effect } from "@web/core/utils/reactive";
import { batched } from "@point_of_sale/utils";

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

        bus_service.addEventListener("notification", ({ detail }) => {
            for (const message of detail) {
                this.dispatch(message);
            }
        });
    }

    dispatch(message) {
        if (message.type === "ORDER_STATE_CHANGED") {
            this.ws_changeOrderState(message.payload.access_token, message.payload.state);
        }
    }

    ws_changeOrderState(access_token, state) {
        this.selfOrder.changeOrderState(access_token, state);
    }
}

export const SelfOrderBusService = {
    dependencies: SelfOrderBus.serviceDependencies,
    async start(env, deps) {
        return new SelfOrderBus(env, deps);
    },
};

registry.category("services").add("self_order_bus_service", SelfOrderBusService);
