/** @odoo-module **/

import { KanbanController } from "@web/views/kanban/kanban_controller";

import { preSuperSetup, useDocumentView } from "@documents/views/hooks";
import { useState } from "@odoo/owl";

export class DocumentsKanbanController extends KanbanController {
    setup() {
        preSuperSetup();
        super.setup(...arguments);
        const properties = useDocumentView(this.documentsViewHelpers());
        Object.assign(this, properties);

        this.documentStates = useState({
            inspectedDocuments: [],
            previewStore: {},
        });
    }

    get modelParams() {
        const modelParams = super.modelParams;
        modelParams.multiEdit = true;
        return modelParams;
    }

    /**
     * Override this to add view options.
     */
    documentsViewHelpers() {
        return {
            getSelectedDocumentsElements: () =>
                this.root.el.querySelectorAll(".o_kanban_record.o_record_selected"),
            setInspectedDocuments: (inspectedDocuments) => {
                this.documentStates.inspectedDocuments = inspectedDocuments;
            },
            setPreviewStore: (previewStore) => {
                this.documentStates.previewStore = previewStore;
            },
        };
    }
}
DocumentsKanbanController.template = "documents.DocumentsKanbanView";
