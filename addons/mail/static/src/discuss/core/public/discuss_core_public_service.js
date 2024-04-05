import { reactive } from "@odoo/owl";

import { registry } from "@web/core/registry";

export class DiscussCorePublic {
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    constructor(env, services) {
        this.env = env;
        this.busService = services["bus_service"];
    }

    setup() {
        this.store.isReady.then(() => this.busService.start());
    }
}
export const discussCorePublic = {
    dependencies: ["bus_service"],
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    start(env, services) {
        const discussPublic = reactive(new DiscussCorePublic(env, services));
        discussPublic.setup();
        return discussPublic;
    },
};

registry.category("services").add("discuss.core.public", discussCorePublic);
