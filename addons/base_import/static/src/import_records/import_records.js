/** @odoo-module native */
import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { exprToBoolean } from "@web/core/utils/format/strings";
import { useService } from "@web/core/utils/hooks";
import { COG_GROUP, isActWindowView } from "@web/search/cog_menu/cog_menu_group";
import { CogMenuItem } from "@web/search/cog_menu/cog_menu_item";

const cogMenuRegistry = registry.category("cogMenu");

/**
 * 'Import records' menu
 *
 * This component is used to import the records for particular model.
 * @extends Component
 */
export class ImportRecords extends Component {
    static template = "base_import.ImportRecords";
    static components = { CogMenuItem };
    static props = {};

    setup() {
        this.action = useService("action");
    }

    //---------------------------------------------------------------------
    // Protected
    //---------------------------------------------------------------------

    importRecords() {
        const { context, resModel } = this.env.searchModel;
        this.action.doAction({
            type: "ir.actions.client",
            tag: "import",
            params: { active_model: resModel, context },
        });
    }
}

export const importRecordsItem = {
    Component: ImportRecords,
    groupNumber: COG_GROUP.DATA,
    isDisplayed: (env) =>
        !env.isSmall &&
        isActWindowView(env, ["kanban", "list"]) &&
        exprToBoolean(env.config.viewArch.getAttribute("import"), true) &&
        exprToBoolean(env.config.viewArch.getAttribute("create"), true),
};

cogMenuRegistry.add("import-menu", importRecordsItem, { sequence: 10 });
