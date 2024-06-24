/** @odoo-module */

import { registry } from "@web/core/registry";
import { Order } from "@point_of_sale/app/store/models";

export class PosBus {
    static serviceDependencies = ["pos", "orm", "bus_service"];

    constructor(...args) {
        this.setup(...args);
    }

    setup(env, { pos, orm, bus_service }) {
        this.pos = pos;
        this.orm = orm;

        bus_service.addChannel(`pos_session-${pos.pos_session.id}-${pos.pos_session.access_token}`);
        bus_service.addEventListener("notification", ({ detail }) => {
            for (const message of detail) {
                this.dispatch(message);
            }
        });
    }

    async dispatch(message) {
        if (message.type === "POS_SELF_ORDER_PAID") {
            const fetchedOrders = await this.orm.call("pos.order", "export_for_ui", [
                message.payload,
            ]);
            const order = new Order(
                { env: this.pos.env },
                { pos: this.pos, json: fetchedOrders[0] }
            );
            this.pos.sendOrderInPreparation(order);
        }
    }
}

export const posBusService = {
    dependencies: PosBus.serviceDependencies,
    async start(env, deps) {
        return new PosBus(env, deps);
    },
};

registry.category("services").add("pos_bus", posBusService);
