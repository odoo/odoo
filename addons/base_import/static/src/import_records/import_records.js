/** @odoo-module **/

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
            params: { model: resModel, context }
        });
    }
}

ImportRecords.template = "base_import.ImportRecords";

const importRecordsItem = {
    Component: ImportRecords,
    groupNumber: 4,
    isDisplayed: ({ config, isSmall }) =>
        !isSmall &&
        config.actionType === "ir.actions.act_window" &&
        ["kanban", "list"].includes(config.viewType)
        // TODO: add arch info to searchModel?
        // !!JSON.parse(env.view.arch.attrs.import || "1") &&
        // !!JSON.parse(env.view.arch.attrs.create || "1"),
};

favoriteMenuRegistry.add("import-menu", importRecordsItem, { sequence: 1 });
