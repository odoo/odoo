import { STATIC_COG_GROUP_ACTION_ADVANCED } from "./documents_cog_menu_group";
import { DocumentsCogMenuItem } from "./documents_cog_menu_item";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class DocumentsCogMenuItemDetails extends DocumentsCogMenuItem {
    setup() {
        this.icon = "fa-info-circle";
        this.label = _t("Info & Tags");
        this.documentService = useService("document.document");
        super.setup();
    }

    async doActionOnFolder(folder) {
        this.documentService.toggleChatterState();
    }
}

export const documentsCogMenuItemDetails = {
    Component: DocumentsCogMenuItemDetails,
    groupNumber: STATIC_COG_GROUP_ACTION_ADVANCED,
    isDisplayed: (env) =>
        DocumentsCogMenuItem.isVisible(
            env,
            ({ documentService, folder }) =>
                documentService.userIsInternal && typeof folder.id === "number"
        ),
};
