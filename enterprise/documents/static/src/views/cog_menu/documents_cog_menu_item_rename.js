import { STATIC_COG_GROUP_ACTION_BASIC } from "./documents_cog_menu_group";
import { DocumentsCogMenuItem } from "./documents_cog_menu_item";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class DocumentsCogMenuItemRename extends DocumentsCogMenuItem {
    setup() {
        this.icon = "fa-edit";
        this.label = _t("Rename");
        super.setup();
        this.documentService = useService("document.document");
    }

    async doActionOnFolder(folder) {
        await this.documentService.openDialogRename(folder.id);
        await this.reload();
    }
}

export const documentsCogMenuItemRename = {
    Component: DocumentsCogMenuItemRename,
    groupNumber: STATIC_COG_GROUP_ACTION_BASIC,
    isDisplayed: (env) =>
        DocumentsCogMenuItem.isVisible(env, ({ folder, documentService }) =>
            documentService.isEditable(folder)
        ),
};
