/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { QuotationDocumentKanbanRecord } from "@sale_pdf_quote_builder/js/quotation_document_kanban/quotation_document_kanban_record";
import { FileUploadProgressContainer } from "@web/core/file_upload/file_upload_progress_container";
import { FileUploadProgressKanbanRecord } from "@web/core/file_upload/file_upload_progress_record";

export class QuotationDocumentKanbanRenderer extends KanbanRenderer {
    static components = {
        ...KanbanRenderer.components,
        FileUploadProgressContainer,
        FileUploadProgressKanbanRecord,
        KanbanRecord: QuotationDocumentKanbanRecord,
    };
    static template = "sale_pdf_quote_builder.QuotationDocumentKanbanRenderer";
    setup() {
        super.setup();
        this.fileUploadService = useService("file_upload");
    }
}
