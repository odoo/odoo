/** @odoo-module native */
import { COG_GROUP } from "@web/search/cog_menu/cog_menu_group";
import { DocumentsCogMenuItem } from "./document_cog_menu_item.js";
import { _t } from "@web/core/translation";

export class DocumentsCogMenuItemAutomations extends DocumentsCogMenuItem {
    setup() {
        this.icon = "fa-solid fa-robot";
        this.label = _t("Automations…");
        super.setup();
    }

    async doActionOnFolder(folder) {
        this.env?.documentsView.bus.trigger("documents-open-automations", {
            folderId: folder.id,
            folderDisplayName: folder.display_name,
        });
    }
}

export const documentsCogMenuItemAutomations = {
    Component: DocumentsCogMenuItemAutomations,
    groupNumber: COG_GROUP.APP,
    isDisplayed: (env) =>
        env.model.documentService.userIsDocumentUser &&
        DocumentsCogMenuItem.isVisible(env, ({ folder, documentService }) =>
            documentService.isEditable(folder),
        ),
};
