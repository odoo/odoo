/** @odoo-module **/

import { preSuperSetup, useDocumentView } from "@documents/views/hooks";
import { DocumentsControllerMixin } from "@documents/views/documents_controller_mixin";
import { onMounted, useRef, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { KanbanController } from "@web/views/kanban/kanban_controller";

export class DocumentsKanbanController extends DocumentsControllerMixin(KanbanController) {
    static template = "documents.DocumentsKanbanView";
    setup() {
        preSuperSetup();
        super.setup(...arguments);
        this.documentService = useService("document.document");
        this.uploadFileInputRef = useRef("uploadFileInput");
        const properties = useDocumentView(this.documentsViewHelpers());
        Object.assign(this, properties);

        this.documentStates = useState({
            previewStore: {},
        });

        /**
         * Open document preview when the page is accessed from an activity link
         * @_get_access_action
         */
        onMounted(() => {
            const initData = this.documentService.initData;
            if (initData.documentId) {
                const document = this.model.root.records.find(
                    (record) => record.data.id === initData.documentId
                );
                if (document) {
                    document.selected = true;
                    if (initData.openPreview) {
                        initData.openPreview = false;
                        document.onClickPreview(new Event("click"));
                    }
                }
            }
        });
    }

    /**
     * Override this to add view options.
     */
    documentsViewHelpers() {
        return {
            getSelectedDocumentsElements: () =>
                this.root?.el?.querySelectorAll(".o_kanban_record.o_record_selected") || [],
            setPreviewStore: (previewStore) => {
                this.documentStates.previewStore = previewStore;
            },
            isRecordPreviewable: this.isRecordPreviewable.bind(this),
        };
    }

    isRecordPreviewable(record) {
        return record.isViewable();
    }

    /**
     * Borrowed from ListController for ListView.Selection.
     */
    onUnselectAll() {
        this.model.root.selection.forEach((record) => {
            record.toggleSelection(false);
        });
        this.model.root.selectDomain(false);
    }
}
