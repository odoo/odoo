import { Component, usePlugin } from "@odoo/owl";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { ORM } from "@web/core/orm_plugin";
import { registry } from "@web/core/registry";
import { useEnv } from "@web/owl2/utils";

const cogMenuRegistry = registry.category("cogMenu");

export class ResetModuleStateCogMenu extends Component {
    static template = "base_setup.ResetModuleStateCogMenu";
    static components = { DropdownItem };

    async resetModuleState() {
        await this.env.services.orm.call("ir.module.module", "button_reset_state", [], {});
        window.location.reload();
    }
}

cogMenuRegistry.add("reset-module-state-cog-menu", {
    Component: ResetModuleStateCogMenu,
    async isDisplayed() {
        const env = useEnv();
        const orm = usePlugin(ORM);
        return (
            env.searchModel.resModel === "ir.module.module" &&
            env.config.viewType !== "form" &&
            (await orm.call("ir.module.module", "check_module_update", [], {}))
        );
    },
});
