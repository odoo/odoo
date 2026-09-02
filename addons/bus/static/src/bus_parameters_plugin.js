import { Plugin, signal, usePlugin } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { services } from "@web/core/services";

export class BusParametersPlugin extends Plugin {
    serverURL = signal(window.origin);
}

services.add(BusParametersPlugin);

/**
 * -----------------------------------------------------------------------------
 * @todo owl3 migration
 * temporary - to remove when all use of the bus_parameters service are removed
 * -----------------------------------------------------------------------------
 */
export const busParametersService = {
    start() {
        const busParametersPlugin = usePlugin(BusParametersPlugin);
        return {
            get serverURL() {
                return busParametersPlugin.serverURL();
            },
        };
    },
};

registry.category("services").add("bus.parameters", busParametersService);
