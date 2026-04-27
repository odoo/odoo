import { Component } from "@odoo/owl";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useService } from "@web/core/utils/hooks";

/**
 * Allow to define a menu entry for the CogMenu by extending it.
 *
 * The sub classe must define:
 * - icon member variable (ex.: "fa-edit")
 * - label member variable (ex.: _t("Edit"))
 * - override the method doActionOnFolder (ex: to open the edit form)
 *
 * @extends Component
 */
export class DocumentsCogMenuItem extends Component {
    static template = "documents.DocumentCogMenuItem";
    static components = { DropdownItem };
    static props = {};

    static isVisible({ config, searchModel, services }, isVisibleAdditional = false) {
        if (!(config && searchModel && searchModel.resModel === "documents.document" && services)) {
            return false;
        }
        const folder = searchModel?.getSelectedFolder();
        const documentService = services["document.document"];
        return (
            folder &&
            documentService &&
            ["kanban", "list"].includes(config.viewType) &&
            (!isVisibleAdditional ||
                isVisibleAdditional({ folder, config, searchModel, documentService }))
        );
    }

    setup() {
        this.action = useService("action");
    }

    async onItemSelected() {
        const folder = this.env?.searchModel?.getSelectedFolder();
        if (!folder) {
            return;
        }
        await this.doActionOnFolder(folder);
    }

    async reload() {
        await this.env.searchModel._reloadSearchModel(true);
        await this.env.model.load();
        await this.env.model.notify();
    }

    async doActionOnFolder(folder) {}
}
