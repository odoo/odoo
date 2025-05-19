import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";

const cogMenuRegistry = registry.category("cogMenu");

export class ResetModuleStateCogMenu extends Component {
    static template = "base_setup.ResetModuleStateCogMenu";
    static components = { DropdownItem };
    static props = {};

    async resetModuleState() {
        await this.env.services.orm.call("ir.module.module", "button_reset_state", [], {});
        window.location.reload();
    }
}

cogMenuRegistry.add("reset-module-state-cog-menu", {
    Component: ResetModuleStateCogMenu,
    isDisplayed: async ({ config, searchModel, services }) =>
        searchModel.resModel === "ir.module.module" &&
        config.viewType !== "form" &&
        (await services.orm.call("ir.module.module", "check_module_update", [], {})),
});
