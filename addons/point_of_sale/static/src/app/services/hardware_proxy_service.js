import { EventBus } from "@odoo/owl";
import { registry } from "@web/core/registry";

/**
 * This object interfaces with the local proxy to communicate to the various hardware devices
 * connected to the Point of Sale. As the communication only goes from the POS to the proxy,
 * methods are used both to signal an event, and to fetch information. Maybe could be improved
 * by using the bus for two-way communication?
 */
export class HardwareProxy extends EventBus {
    static serviceDependencies = [];
    constructor() {
        super();
        this.setup(...arguments);
    }
    setup() {
        this.deviceControllers = {};
    }
}

export const hardwareProxyService = {
    dependencies: HardwareProxy.serviceDependencies,
    start(env, deps) {
        return new HardwareProxy(deps);
    },
};

registry.category("services").add("hardware_proxy", hardwareProxyService);
