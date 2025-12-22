import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { exprToBoolean } from "@web/core/utils/strings";
import { STATIC_ACTIONS_GROUP_NUMBER } from "@web/search/action_menus/action_menus";

import { Component } from "@odoo/owl";

const cogMenuRegistry = registry.category("cogMenu");

/**
 * 'Export All' menu
 *
 * This component is used to export all the records for particular model.
 * @extends Component
 */
export class ExportAll extends Component {
    static template = "web.ExportAll";
    static components = { DropdownItem };
    static props = {};

    //---------------------------------------------------------------------
    // Protected
    //---------------------------------------------------------------------

    async onDirectExportData() {
        this.env.searchModel.trigger("direct-export-data");
    }
}

export const exportAllItem = {
    Component: ExportAll,
    groupNumber: STATIC_ACTIONS_GROUP_NUMBER,
    isDisplayed: async (env) =>
        env.config.viewType === "list" &&
        !env.model.root.selection.length &&
        (await user.hasGroup("base.group_allow_export")) &&
        exprToBoolean(env.config.viewArch.getAttribute("export_xlsx"), true),
};

cogMenuRegistry.add("export-all-menu", exportAllItem, { sequence: 10 });
