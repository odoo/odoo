/** @odoo-module native */
import { Component, status, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useDebounced } from "@web/core/utils/timing";
import { Dropdown, DropdownItem } from "@web/components/dropdown";
import { COG_GROUP } from "@web/search/cog_menu/cog_menu_group";
import { _t } from "@web/core/translation";
import { isDocumentsCogMenuItemVisible } from "./document_cog_menu_item.js";

export class DocumentCogMenuPinAction extends Component {
    static template = "document.DocumentCogMenuPinAction";
    static components = { Dropdown, DropdownItem };
    static props = {};

    static isVisible = isDocumentsCogMenuItemVisible;

    setup() {
        this.action = useService("action");
        this.documentService = useService("document.document");
        this.notification = useService("notification");

        this.documentsState = useState({ actions: [], isLoading: true });
        this._reloadSearchModel = useDebounced(() => {
            this.env.searchModel._reloadSearchModel(true);
        }, 1500);

        const folderId = this.env.searchModel.getSelectedFolderId();
        this.documentService.getActions(folderId).then((actions) => {
            if (status(this) === "destroyed") {
                return;
            }
            this.documentsState.actions = actions;
            this.documentsState.isLoading = false;
        });
    }

    async onEnableAction(actionId) {
        const currentFolderId = this.env.searchModel.getSelectedFolderId();
        if (!currentFolderId || typeof currentFolderId !== "number") {
            this.notification.add(_t("You can not pin actions for that folder."), {
                type: "warning",
            });
            return;
        }

        const action = this.documentsState.actions.find((a) => a.id === actionId);
        if (!action) {
            return;
        }
        action.is_embedded = !action.is_embedded;
        try {
            await this.documentService.enableAction(currentFolderId, actionId);
        } catch {
            action.is_embedded = !action.is_embedded;
        }
        this._reloadSearchModel();
    }
}

export const documentCogMenuPinAction = {
    Component: DocumentCogMenuPinAction,
    groupNumber: COG_GROUP.APP,
    isDisplayed: (env) =>
        env.model.documentService.userIsDocumentUser &&
        DocumentCogMenuPinAction.isVisible(env, ({ folder, documentService }) =>
            documentService.isEditable(folder),
        ),
};
