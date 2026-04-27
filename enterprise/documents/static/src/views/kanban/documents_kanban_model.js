/** @odoo-module **/

import { Domain } from "@web/core/domain";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { RelationalModel } from "@web/model/relational_model/relational_model";
import {
    DocumentsModelMixin,
    DocumentsRecordMixin,
} from "../documents_model_mixin";

export class DocumentsKanbanModel extends DocumentsModelMixin(RelationalModel) {
    setup() {
        super.setup(...arguments);
        this.documentService = useService("document.document");
    }

    /**
     * Ensure that when coming for a specific document, it is present as the first document
     * on the first page. Notify the user if the requested document wasn't found.
     */
    async _loadData(config) {
        const data = await super._loadData(config);
        // This getter resets the DocumentIdToRestore, we'll restore it if we do have the record.
        const documentIdToRestore = this.documentService.getOnceDocumentIdToRestore();
        if (!documentIdToRestore) {
            return data;
        }
        const idxToRestore = data.records.findIndex((r) => r.id === documentIdToRestore);
        if (idxToRestore !== -1) {
            const recordToRestore = data.records.splice(idxToRestore, 1)[0]; // take it out
            data.records.splice(0, 0, recordToRestore); // put it at the top of the list
            this.documentService.documentIdToRestore = documentIdToRestore;
        } else {
            const missingData = await super._loadData({
                ...config,
                domain: Domain.and([config.domain, [["id", "=", documentIdToRestore]]]).toList(),
                limit: 1,
            });
            if (missingData?.records?.length) {
                data.records.splice(0, 0, missingData.records[0]); // put it at the top of the list
                data.records.pop(); // Remove the last item to not overflow page
                this.documentService.documentIdToRestore = documentIdToRestore;
            } else {
                this.notification.add(_t("Document not found or inaccessible."), {
                    type: "danger",
                });
            }
        }
        return data;
    }
}

export class DocumentsKanbanRecord extends DocumentsRecordMixin(RelationalModel.Record) {

    async onReplaceDocument(ev) {
        if (!ev.target.files.length) {
            return;
        }
        await this.model.env.documentsView.bus.trigger("documents-upload-files", {
            files: ev.target.files,
            accessToken: this.data.access_token,
            context: {
                document_id: this.data.id,
            }
        });
        ev.target.value = "";
    }
}
DocumentsKanbanModel.Record = DocumentsKanbanRecord;
