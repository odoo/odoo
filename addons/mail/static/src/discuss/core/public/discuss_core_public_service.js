/* @odoo-module */

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
        this.messagingService = services["mail.messaging"];
    }

    setup() {
        this.messagingService.isReady.then(() => this.busService.start());
    }
}
export const discussCorePublic = {
    dependencies: ["bus_service", "mail.messaging"],
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
