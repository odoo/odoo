import { registry } from "@web/core/registry";
import { plugin, Plugin } from "@odoo/owl";
import { services } from "@web/core/services";

export class BusParametersPlugin extends Plugin {
    serverURL = window.origin;
}

services.add(BusParametersPlugin);

/**
 * -----------------------------------------------------------------------------
 * @todo owl3 migration
 * temporary - to remove when all use of the bus_parameters service are removed
 * -----------------------------------------------------------------------------
 */
registry.category("services").add("bus.parameters", {
    start() {
        return plugin(BusParametersPlugin);
    }
});
