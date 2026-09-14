/** @odoo-module native */
import { documentActionRules } from "@document/views/document_action_rules";
import { COG_GROUP } from "@web/search/cog_menu/cog_menu_group";
import { DocumentsCogMenuItem } from "./document_cog_menu_item.js";
import { _t } from "@web/core/translation";

export class DocumentsCogMenuItemRename extends DocumentsCogMenuItem {
    setup() {
        this.icon = "fa-solid fa-pen-to-square";
        this.label = _t("Rename…");
        super.setup();
    }

    async doActionOnFolder(folder) {
        await this.documentService.openDialogRename(folder.id);
        await this.reload();
    }
}

export const documentsCogMenuItemRename = {
    Component: DocumentsCogMenuItemRename,
    groupNumber: COG_GROUP.RECORD,
    isDisplayed: (env) =>
        DocumentsCogMenuItem.isVisible(env, ({ folder, documentService }) =>
            documentActionRules.rename(documentService, folder),
        ),
};
