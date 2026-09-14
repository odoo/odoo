/** @odoo-module native */
import { documentActionRules } from "@document/views/document_action_rules";
import { COG_GROUP } from "@web/search/cog_menu/cog_menu_group";
import { DocumentsCogMenuItem } from "./document_cog_menu_item.js";
import { _t } from "@web/core/translation";

export class DocumentsCogMenuItemShare extends DocumentsCogMenuItem {
    setup() {
        this.icon = "fa-solid fa-share-nodes";
        this.label = _t("Share…");
        super.setup();
    }

    async doActionOnFolder(folder) {
        await this.documentService.openSharingDialog([folder.id]);
    }
}

export const documentsCogMenuItemShare = {
    Component: DocumentsCogMenuItemShare,
    groupNumber: COG_GROUP.RECORD,
    isDisplayed: (env) =>
        DocumentsCogMenuItem.isVisible(
            env,
            ({ folder, documentService }) =>
                documentService.userIsInternal &&
                documentActionRules.share(documentService, folder),
        ),
};
