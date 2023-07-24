/* @odoo-module */

import { reactive } from "@odoo/owl";

import { registry } from "@web/core/registry";

export class DiscussCorePublic {
    constructor(env, services) {
        /** @type {import("@web/env").OdooEnv} */
        this.env = env;
        /** @type {ReturnType<typeof import("@bus/services/bus_service").busService.start>} */
        this.busService = services["bus_service"];
        /** @type {import("@mail/core/common/messaging_service").Messaging} */
        this.messagingService = services["mail.messaging"];
    }

    setup() {
        this.messagingService.isReady.then(() => this.busService.start());
    }
}
export const discussCorePublic = {
    dependencies: ["bus_service", "mail.messaging"],

    start(env, services) {
        const discussPublic = reactive(new DiscussCorePublic(env, services));
        discussPublic.setup();
        return discussPublic;
    },
};

registry.category("services").add("discuss.core.public", discussCorePublic);
