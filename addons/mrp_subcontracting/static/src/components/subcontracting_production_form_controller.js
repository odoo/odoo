/** @odoo-module native */
import { registry } from "@web/core/registry";
import { _t } from "@web/core/translation";
import { COG_GROUP } from "@web/search/cog_menu/cog_menu_group";
import { FormController, formView } from "@web/views/form";

class SubcontractingProductionFormController extends FormController {
    get actionMenuItems() {
        return {
            action: [
                {
                    key: "assign",
                    groupNumber: COG_GROUP.APP,
                    icon: "fa-solid fa-boxes-stacked",
                    description: _t("Check Availability"),
                    callback: async () => {
                        await this.model.orm.call("mrp.production", "action_assign", [
                            this.model.root.resId,
                        ]);
                        await this.model.load();
                    },
                },
                {
                    key: "split",
                    groupNumber: COG_GROUP.APP,
                    icon: "fa-solid fa-code-branch",
                    description: _t("Create New Production"),
                    callback: async () => {
                        const res = await this.model.orm.call(
                            "mrp.production",
                            "action_split_subcontracting",
                            [this.model.root.resId],
                        );
                        this.actionService.doAction(res);
                    },
                },
            ],
        };
    }
}

registry.category("views").add("subcontracting_production_form", {
    ...formView,
    Controller: SubcontractingProductionFormController,
});
