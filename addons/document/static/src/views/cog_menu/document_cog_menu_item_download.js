/** @odoo-module native */
import { documentActionRules } from "@document/views/document_action_rules";
import { COG_GROUP } from "@web/search/cog_menu/cog_menu_group";
import { DocumentsCogMenuItem } from "./document_cog_menu_item.js";
import { _t } from "@web/core/translation";

export class DocumentsCogMenuItemDownload extends DocumentsCogMenuItem {
    setup() {
        this.icon = "fa-solid fa-download";
        this.label = _t("Download");
        super.setup();
    }

    async doActionOnFolder(folder) {
        this.action.doAction({
            type: "ir.actions.act_url",
            url: `/documents/content/${encodeURIComponent(folder.access_token)}`,
        });
    }
}

export const documentsCogMenuItemDownload = {
    Component: DocumentsCogMenuItemDownload,
    groupNumber: COG_GROUP.DATA,
    isDisplayed: (env) =>
        DocumentsCogMenuItem.isVisible(env, ({ folder, documentService }) =>
            documentActionRules.download(documentService, folder),
        ),
};
