/** @odoo-module */

import { registry } from "@web/core/registry";

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

    dispatch(message) {}
}

export const posBusService = {
    dependencies: PosBus.serviceDependencies,
    async start(env, deps) {
        return new PosBus(env, deps);
    },
};

registry.category("services").add("pos_bus", posBusService);
