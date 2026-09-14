/** @odoo-module native */
import { reloadDocumentsView } from "@document/views/hooks";
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { CogMenuItem } from "@web/search/cog_menu/cog_menu_item";

/**
 * @param {Object} env
 * @param {Function|false} [isVisibleAdditional]
 * @returns {boolean}
 */
export function isDocumentsCogMenuItemVisible(
    { config, searchModel, services },
    isVisibleAdditional = false,
) {
    if (!(
        config &&
        searchModel &&
        searchModel.resModel === "document.document" &&
        services
    )) {
        return false;
    }
    const folder = searchModel.getSelectedFolder();
    const documentService = services["document.document"];
    return Boolean(
        folder &&
        documentService &&
        ["kanban", "list"].includes(config.viewType) &&
        (!isVisibleAdditional ||
            isVisibleAdditional({ folder, config, searchModel, documentService })),
    );
}

export class DocumentsCogMenuItem extends Component {
    static template = "document.DocumentCogMenuItem";
    static components = { CogMenuItem };
    static props = {};

    static isVisible = isDocumentsCogMenuItemVisible;

    setup() {
        this.action = useService("action");
        this.documentService = useService("document.document");
    }

    async onItemSelected() {
        const folder = this.env?.searchModel?.getSelectedFolder();
        if (!folder) {
            return;
        }
        await this.doActionOnFolder(folder);
    }

    async reload() {
        await reloadDocumentsView(this.env);
    }

    async doActionOnFolder() {}
}
