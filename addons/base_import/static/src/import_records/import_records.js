/** @odoo-module **/

import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const { Component } = owl;
const favoriteMenuRegistry = registry.category("favoriteMenu");

/**
 * 'Import records' menu
 *
 * This component is used to import the records for particular model.
 * @extends Component
 */
export class ImportRecords extends Component {
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

ImportRecords.template = "base_import.ImportRecords";
ImportRecords.components = { DropdownItem };

export const importRecordsItem = {
    Component: ImportRecords,
    groupNumber: 4,
    isDisplayed: ({ config, isSmall }) =>
        !isSmall &&
        config.actionType === "ir.actions.act_window" &&
        ["kanban", "list"].includes(config.viewType) &&
        !!JSON.parse(config.viewArch.getAttribute("import") || "1") &&
        !!JSON.parse(config.viewArch.getAttribute("create") || "1"),
};

favoriteMenuRegistry.add("import-menu", importRecordsItem, { sequence: 1 });
