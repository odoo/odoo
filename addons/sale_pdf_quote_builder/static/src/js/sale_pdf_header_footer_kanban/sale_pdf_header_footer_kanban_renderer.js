/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { SalePdfHeaderFooterKanbanRecord } from "@sale_pdf_quote_builder/js/sale_pdf_header_footer_kanban/sale_pdf_header_footer_kanban_record";
import { FileUploadProgressContainer } from "@web/core/file_upload/file_upload_progress_container";
import { FileUploadProgressKanbanRecord } from "@web/core/file_upload/file_upload_progress_record";

export class SalePdfHeaderFooterKanbanRenderer extends KanbanRenderer {
    static components = {
        ...KanbanRenderer.components,
        FileUploadProgressContainer,
        FileUploadProgressKanbanRecord,
        KanbanRecord: SalePdfHeaderFooterKanbanRecord,
    };
    static template = "sale_pdf_quote_builder.SalePdfHeaderFooterKanbanRenderer";
    setup() {
        super.setup();
        this.fileUploadService = useService("file_upload");
    }
}
