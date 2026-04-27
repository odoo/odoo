import { STATIC_COG_GROUP_ACTION_CLEANUP } from "./documents_cog_menu_group";
import { DocumentsCogMenuItem } from "./documents_cog_menu_item";
import { toggleArchive } from "@documents/views/hooks";
import { _t } from "@web/core/l10n/translation";

export class DocumentsCogMenuItemArchive extends DocumentsCogMenuItem {
    setup() {
        this.icon = "fa-trash";
        this.label = _t("Move to trash");
        super.setup();
    }

    async doActionOnFolder(folder) {
        await toggleArchive(this.env.model, "documents.document", folder.id, true);
        await this.reload();
    }
}

export const documentsCogMenuItemArchive = {
    Component: DocumentsCogMenuItemArchive,
    groupNumber: STATIC_COG_GROUP_ACTION_CLEANUP,
    isDisplayed: (env) =>
        DocumentsCogMenuItem.isVisible(
            env,
            ({ folder, documentService }) =>
                documentService.userIsInternal && documentService.isEditable(folder)
        ),
};
