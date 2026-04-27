import { STATIC_COG_GROUP_ACTION_ADVANCED } from "./documents_cog_menu_group";
import { DocumentsCogMenuItem } from "./documents_cog_menu_item";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class DocumentsCogMenuItemStar extends DocumentsCogMenuItem {
    setup(isAdd) {
        this.icon = isAdd ? "fa-star-o" : "fa-star";
        this.label = isAdd ? _t("Add star") : _t("Remove star");
        super.setup();
        this.documentService = useService("document.document");
    }

    async doActionOnFolder(folder) {
        await this.documentService.toggleFavorite(folder);
        await this.reload();
    }
}

export class DocumentsCogMenuItemStarAdd extends DocumentsCogMenuItemStar {
    setup() {
        super.setup(true);
    }
}

export class DocumentsCogMenuItemStarRemove extends DocumentsCogMenuItemStar {
    setup() {
        super.setup(false);
    }
}

export const documentsCogMenuItemStarAdd = {
    Component: DocumentsCogMenuItemStarAdd,
    groupNumber: STATIC_COG_GROUP_ACTION_ADVANCED,
    isDisplayed: (env) =>
        DocumentsCogMenuItem.isVisible(
            env,
            ({ folder, documentService }) =>
                documentService.isEditable(folder) && !folder.is_favorited
        ),
};

export const documentsCogMenuItemStarRemove = {
    Component: DocumentsCogMenuItemStarRemove,
    groupNumber: STATIC_COG_GROUP_ACTION_ADVANCED,
    isDisplayed: (env) =>
        DocumentsCogMenuItem.isVisible(
            env,
            ({ folder, documentService }) =>
                documentService.isEditable(folder) && folder.is_favorited
        ),
};
