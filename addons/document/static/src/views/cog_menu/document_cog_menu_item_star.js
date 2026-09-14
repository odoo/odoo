/** @odoo-module native */
import { COG_GROUP } from "@web/search/cog_menu/cog_menu_group";
import { DocumentsCogMenuItem } from "./document_cog_menu_item.js";
import { _t } from "@web/core/translation";

export class DocumentsCogMenuItemStar extends DocumentsCogMenuItem {
    setup(isAdd) {
        this.icon = isAdd ? "fa-regular fa-star" : "fa-solid fa-star";
        this.label = isAdd ? _t("Add Star") : _t("Remove Star");
        super.setup();
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
    groupNumber: COG_GROUP.RECORD,
    isDisplayed: (env) =>
        DocumentsCogMenuItem.isVisible(
            env,
            ({ folder, documentService }) =>
                documentService.isEditable(folder) && !folder.is_user_favorite,
        ),
};

export const documentsCogMenuItemStarRemove = {
    Component: DocumentsCogMenuItemStarRemove,
    groupNumber: COG_GROUP.RECORD,
    isDisplayed: (env) =>
        DocumentsCogMenuItem.isVisible(
            env,
            ({ folder, documentService }) =>
                documentService.isEditable(folder) && folder.is_user_favorite,
        ),
};
