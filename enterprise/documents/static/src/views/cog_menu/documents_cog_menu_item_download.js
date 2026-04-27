import { STATIC_COG_GROUP_ACTION_BASIC } from "./documents_cog_menu_group";
import { DocumentsCogMenuItem } from "./documents_cog_menu_item";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class DocumentsCogMenuItemDownload extends DocumentsCogMenuItem {
    setup() {
        this.icon = "fa-download";
        this.label = _t("Download");
        super.setup();
        this.action = useService("action");
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
    groupNumber: STATIC_COG_GROUP_ACTION_BASIC,
    isDisplayed: (env) =>
        DocumentsCogMenuItem.isVisible(env, ({ folder, documentService }) =>
            documentService.canDownload(folder)
        ),
};
