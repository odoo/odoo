/** @odoo-module native */
import { COG_GROUP } from "@web/search/cog_menu/cog_menu_group";
import { DocumentsCogMenuItem } from "./document_cog_menu_item.js";
import { _t } from "@web/core/translation";

export class DocumentsCogMenuItemShortcut extends DocumentsCogMenuItem {
    setup() {
        this.icon = "fa-solid fa-up-right-from-square";
        this.label = _t("Add Shortcut…");
        super.setup();
    }

    async doActionOnFolder(folder) {
        await this.documentService.openOperationDialog({
            documents: [{ id: folder.id, name: folder.display_name }],
            operation: "shortcut",
            onClose: () => this.reload(),
        });
        await this.reload();
    }
}

export const documentsCogMenuItemShortcut = {
    Component: DocumentsCogMenuItemShortcut,
    groupNumber: COG_GROUP.RECORD,
    isDisplayed: (env) =>
        DocumentsCogMenuItem.isVisible(
            env,
            ({ folder, documentService }) =>
                documentService.isEditable(folder) &&
                !folder.shortcut_document_id &&
                typeof folder.user_folder_id === "number",
        ),
};
