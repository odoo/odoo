/** @odoo-module native */
import { COG_GROUP } from "@web/search/cog_menu/cog_menu_group";
import { DocumentsCogMenuItem } from "./document_cog_menu_item.js";
import { _t } from "@web/core/translation";

export class DocumentsCogMenuItemArchive extends DocumentsCogMenuItem {
    setup() {
        this.icon = "fa-regular fa-trash-can";
        this.label = _t("Move to Trash");
        super.setup();
    }

    async doActionOnFolder(folder) {
        await this.documentService.moveToTrash([folder.id]);
        await this.reload();
    }
}

export const documentsCogMenuItemArchive = {
    Component: DocumentsCogMenuItemArchive,
    groupNumber: COG_GROUP.RECORD,
    isDisplayed: (env) =>
        DocumentsCogMenuItem.isVisible(
            env,
            ({ folder, documentService }) =>
                documentService.userIsInternal && documentService.isEditable(folder),
        ),
};
