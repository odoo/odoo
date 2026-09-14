/** @odoo-module native */
import { documentActionRules } from "@document/views/document_action_rules";
import { COG_GROUP } from "@web/search/cog_menu/cog_menu_group";
import { DocumentsCogMenuItem } from "./document_cog_menu_item.js";
import { _t } from "@web/core/translation";

export class DocumentsCogMenuItemDetails extends DocumentsCogMenuItem {
    setup() {
        this.icon = "fa-solid fa-circle-info";
        this.label = _t("Info & Tags");
        super.setup();
    }

    async doActionOnFolder() {
        this.documentService.toggleRightPanelVisibility();
    }
}

export const documentsCogMenuItemDetails = {
    Component: DocumentsCogMenuItemDetails,
    groupNumber: COG_GROUP.RECORD,
    isDisplayed: (env) =>
        DocumentsCogMenuItem.isVisible(env, ({ documentService, folder }) =>
            documentActionRules.details(documentService, folder),
        ),
};
