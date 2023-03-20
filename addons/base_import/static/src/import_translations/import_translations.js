/** @odoo-module **/

import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const { Component } = owl;
const favoriteMenuRegistry = registry.category("favoriteMenu");

/**
 * 'Import translations
 *
 * This component is used to import the translations for particular model.
 * @extends Component
 */
export class ImportTranslations extends Component {
    setup() {
        this.action = useService("action");
    }

    //---------------------------------------------------------------------
    // Protected
    //---------------------------------------------------------------------

    importTranslations() {
        const { context } = this.env.searchModel;
        this.action.doAction({
            title: this.env._t("Import Translation"),
            type: "ir.actions.act_window",
            res_model: "base_import.import.translation",
            target: "new",
            views: [[false, "form"]],
            context: context,
        });
    }
}

ImportTranslations.template = "base_import.ImportTranslations";
ImportTranslations.components = { DropdownItem };

export const importTranslationsItem = {
    Component: ImportTranslations,
    groupNumber: 4,
    isDisplayed: ({ config, isSmall }) =>
        !isSmall &&
        config.actionType === "ir.actions.act_window" &&
        ["kanban", "list"].includes(config.viewType) &&
        !!JSON.parse(config.viewArch.getAttribute("import") || "1") &&
        !!JSON.parse(config.viewArch.getAttribute("create") || "1"),
};

favoriteMenuRegistry.add("import-translation-menu", importTranslationsItem, { sequence: 1 });
