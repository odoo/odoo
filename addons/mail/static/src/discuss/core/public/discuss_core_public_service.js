import { registry } from "@web/core/registry";

export const discussCorePublic = {
    dependencies: ["bus_service"],
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    start(env, services) {
        services.bus_service.start();
    },
};

registry.category("services").add("discuss.core.public", discussCorePublic);
