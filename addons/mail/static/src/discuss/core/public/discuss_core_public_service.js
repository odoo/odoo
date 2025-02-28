import { registry } from "@web/core/registry";

export const discussCorePublic = {
    dependencies: ["bus_service"],
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {import("services").ServiceFactories} services
     */
    start(env, services) {},
};

registry.category("services").add("discuss.core.public", discussCorePublic);
