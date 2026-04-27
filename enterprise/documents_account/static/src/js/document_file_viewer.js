/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { FileViewer } from "@documents/attachments/document_file_viewer";

patch(FileViewer.prototype, {
    /**
     * Do not show the Split PDF option for embedded PDF in XML invoices.
     */
    get hasSplitPdf() {
        if (this.documentService.documentList?.initialRecordSelectionLength === 1) {
            if (this.documentService.documentList.selectedDocument.record.data.has_embedded_pdf) {
                return false;
            }
        } else if (
            this.documentService.documentList?.documents.some(
                (document) => document.record.data.has_embedded_pdf
            )
        ) {
            return false;
        }
        return super.hasSplitPdf;
    },
});
