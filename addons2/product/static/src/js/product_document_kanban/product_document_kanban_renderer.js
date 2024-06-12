/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { ProductDocumentKanbanRecord } from "@product/js/product_document_kanban/product_document_kanban_record";
import { FileUploadProgressContainer } from "@web/core/file_upload/file_upload_progress_container";
import { FileUploadProgressKanbanRecord } from "@web/core/file_upload/file_upload_progress_record";

export class ProductDocumentKanbanRenderer extends KanbanRenderer {
    setup() {
        super.setup();
        this.fileUploadService = useService("file_upload");
    }
}

ProductDocumentKanbanRenderer.components = {
    ...KanbanRenderer.components,
    FileUploadProgressContainer,
    FileUploadProgressKanbanRecord,
    KanbanRecord: ProductDocumentKanbanRecord,
};
ProductDocumentKanbanRenderer.template = "product.ProductDocumentKanbanRenderer";
