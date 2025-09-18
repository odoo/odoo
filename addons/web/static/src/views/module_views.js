// @ts-check

/** @module @web/views/module_views - Cog-menu item to reset ir.module.module installation state */

import { Component } from "@odoo/owl";
import { DropdownItem } from "@web/components/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
const cogMenuRegistry = registry.category("cogMenu");

/** Cog-menu item that resets module installation state (only on ir.module.module list views). */
export class ResetModuleStateCogMenu extends Component {
    static template = "web.ResetModuleStateCogMenu";
    static components = { DropdownItem };
    static props = {};

    async resetModuleState() {
        await this.env.services.orm.call(
            "ir.module.module",
            "button_reset_state",
            [],
            {},
        );
        window.location.reload();
    }
}

cogMenuRegistry.add(
    "reset-module-state-cog-menu",
    /** @type {any} */ ({
        Component: ResetModuleStateCogMenu,
        isDisplayed: async ({ config, searchModel, services }) =>
            searchModel.resModel === "ir.module.module" &&
            config.viewType !== "form" &&
            (await services.orm.call(
                "ir.module.module",
                "check_module_update",
                [],
                {},
            )),
    }),
);
