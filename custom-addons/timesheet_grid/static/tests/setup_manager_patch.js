/* @odoo-module */

import { clearRegistryWithCleanup } from "@web/../tests/helpers/mock_env";
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";

import { copyRegistry, setupManager } from "@mail/../tests/helpers/webclient_setup";
const gridComponentRegistry = registry.category("grid_components");
const savedGridComponentRegistry = registry.category("saved_grid_components");

QUnit.begin(() => copyRegistry(gridComponentRegistry, savedGridComponentRegistry));

patch(setupManager, {
    setupServiceRegistries() {
        super.setupServiceRegistries(...arguments);
        // Restore the grid component registry to its original state
        // since it is required by some services.
        clearRegistryWithCleanup(registry.category("grid_components"));
        for (const [name, component] of savedGridComponentRegistry.getEntries()) {
            gridComponentRegistry.add(name, component);
        }
    },
});
