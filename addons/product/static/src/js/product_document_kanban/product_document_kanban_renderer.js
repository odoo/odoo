import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { ProductDocumentKanbanRecord } from "@product/js/product_document_kanban/product_document_kanban_record";

export class ProductDocumentKanbanRenderer extends KanbanRenderer {
    static components = {
        ...KanbanRenderer.components,
        KanbanRecord: ProductDocumentKanbanRecord,
    };
}
