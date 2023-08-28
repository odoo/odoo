/** @odoo-module **/

import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
<<<<<<< HEAD
import { archParseBoolean } from "@web/views/utils";
||||||| parent of f60f7fe52a6 (temp)
=======
import { archParseBoolean } from '@web/views/utils';
>>>>>>> f60f7fe52a6 (temp)
import { Component } from "@odoo/owl";
import { STATIC_ACTIONS_GROUP_NUMBER } from "@web/search/action_menus/action_menus";

const cogMenuRegistry = registry.category("cogMenu");

/**
 * 'Import records' menu
 *
 * This component is used to import the records for particular model.
 * @extends Component
 */
export class ImportRecords extends Component {
    static template = "base_import.ImportRecords";
    static components = { DropdownItem };

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
            params: { model: resModel, context },
        });
    }
}

export const importRecordsItem = {
    Component: ImportRecords,
    groupNumber: STATIC_ACTIONS_GROUP_NUMBER,
    isDisplayed: ({ config, isSmall }) =>
        !isSmall &&
        config.actionType === "ir.actions.act_window" &&
        ["kanban", "list"].includes(config.viewType) &&
<<<<<<< HEAD
        archParseBoolean(config.viewArch.getAttribute("import"), true) &&
        archParseBoolean(config.viewArch.getAttribute("create"), true),
||||||| parent of f60f7fe52a6 (temp)
        !!JSON.parse(config.viewArch.getAttribute("import") || "1") &&
        !!JSON.parse(config.viewArch.getAttribute("create") || "1"),
=======
        archParseBoolean(config.viewArch.getAttribute("import") || "1") &&
        archParseBoolean(config.viewArch.getAttribute("create") || "1"),
>>>>>>> f60f7fe52a6 (temp)
};

cogMenuRegistry.add("import-menu", importRecordsItem, { sequence: 1 });
