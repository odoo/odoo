/** @odoo-module */

import { registry } from "@web/core/registry";

const mockRegistry = registry.category("mock_server");

mockRegistry.add("get_worklocation", function(route, args) {
    return Promise.resolve();
});
