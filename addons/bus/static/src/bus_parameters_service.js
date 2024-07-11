/** @odoo-module */

import { registry } from "@web/core/registry";

export const busParametersService = {
    start() {
        return {
            serverURL: window.origin,
        };
    },
};

registry.category("services").add("bus.parameters", busParametersService);
