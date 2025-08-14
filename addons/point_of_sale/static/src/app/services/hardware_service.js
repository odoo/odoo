import { HWPrinter } from "@point_of_sale/app/utils/printer/hw_printer";
import { EventBus, reactive } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { deduceUrl } from "@point_of_sale/utils";
import { effect } from "@web/core/utils/reactive";

/**
 * This object interfaces with the local proxy to communicate to the various hardware devices
 * connected to the Point of Sale. As the communication only goes from the POS to the proxy,
 * methods are used both to signal an event, and to fetch information. Maybe could be improved
 * by using the bus for two-way communication?
 */
export class PosHardwareService extends EventBus {
    static serviceDependencies = [];

    constructor() {
        super();
        this.setup(...arguments);
    }

    setup() {
        this.devices = new Map();
    }
}

export const HardwareService = {
    dependencies: PosHardwareService.serviceDependencies,
    start(env, deps) {
        return new PosHardwareService(deps);
    },
};

registry.category("services").add("hardware", HardwareService);
