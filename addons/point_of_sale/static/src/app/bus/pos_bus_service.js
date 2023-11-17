/** @odoo-module */

import { registry } from "@web/core/registry";

export class PosBus {
    static serviceDependencies = ["pos", "bus_service"];

    constructor(...args) {
        this.setup(...args);
    }

    setup(env, { pos, bus_service }) {
        this.pos = pos;

        bus_service.addChannel(
            `pos_session-${pos.session.id}-${pos.session.access_token}`
        );
        bus_service.addEventListener("notification", ({ detail }) => {
            for (const message of detail) {
                this.dispatch(message);
            }
        });
    }

    dispatch(message) {}
}

export const posBusService = {
    dependencies: PosBus.serviceDependencies,
    async start(env, deps) {
        return new PosBus(env, deps);
    },
};

registry.category("services").add("pos_bus", posBusService);
