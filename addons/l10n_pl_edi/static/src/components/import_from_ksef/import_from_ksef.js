/** @odoo-module **/

import { Component } from "@odoo/owl";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { STATIC_ACTIONS_GROUP_NUMBER } from "@web/search/action_menus/action_menus";

const cogMenuRegistry = registry.category("cogMenu");

export class ImportFromKsef extends Component {
    static template = "l10n_pl_edi.ImportFromKsef";
    static components = { DropdownItem };
    static props = {};

    setup() {
        this.action = useService("action");
    }

    importFromKsef() {
        const { context } = this.env.searchModel;
        this.action.doActionButton({
            type: "object",
            resModel: "account.move",
            name: "action_l10n_pl_edi_import_from_ksef",
            context,
        });
    }
}

export const importFromKsefItem = {
    Component: ImportFromKsef,
    groupNumber: STATIC_ACTIONS_GROUP_NUMBER,
    isDisplayed: async ({ config, searchModel, services }) => {
        return searchModel.resModel === "account.move" &&
            config.actionType === "ir.actions.act_window" &&
            ["kanban", "list"].includes(config.viewType) &&
            searchModel.context.default_move_type?.startsWith("in_") &&
            await services.orm.call(
            "res.company",
            "l10n_pl_edi_company_has_access_to_ksef",
            [],
            { context: searchModel.context })
    },
};

cogMenuRegistry.add("l10n-pl-edi-import-from-ksef-menu", importFromKsefItem, { sequence: 2 });
