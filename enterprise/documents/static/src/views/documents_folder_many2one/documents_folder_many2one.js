/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Many2OneField, many2OneField } from "@web/views/fields/many2one/many2one_field";

export class DocumentsFolderMany2One extends Many2OneField {
    /**
     * Open the documents kanban view, in the folder instead of redirecting to the form view.
     */
    async openAction() {
        await this.action.doAction("documents.document_action", {
            additionalContext: {
                no_documents_unique_folder_id: true,
                searchpanel_default_folder_id: this.resId,
            },
        });
    }

    onExternalBtnClick() {
        this.openAction();
    }
}

export const documentsFolderMany2One = {
    ...many2OneField,
    component: DocumentsFolderMany2One,
};

registry.category("fields").add("documents_folder_many2one", documentsFolderMany2One);
