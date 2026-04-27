import { STATIC_COG_GROUP_ACTION_PIN } from "./documents_cog_menu_group";
import { DocumentsCogMenuItem } from "./documents_cog_menu_item";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class DocumentsCogMenuItemAutomations extends DocumentsCogMenuItem {
    setup() {
        this.icon = "fa-cog";
        this.label = _t("Automations");
        super.setup();
        this.orm = useService("orm");
        this.dialog = useService("dialog");
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
    groupNumber: STATIC_COG_GROUP_ACTION_PIN,
    isDisplayed: (env) =>
        env.model.documentService.userIsDocumentUser &&
        DocumentsCogMenuItem.isVisible(env, ({ folder, documentService }) =>
            documentService.isEditable(folder)
        ),
};
