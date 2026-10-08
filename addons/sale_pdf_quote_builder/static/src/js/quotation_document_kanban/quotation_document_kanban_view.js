import { productDocumentKanbanView } from "@product/js/product_document_kanban/product_document_kanban_view";
import { registry } from "@web/core/registry";

registry.category("views").add("quotation_document_kanban", productDocumentKanbanView);
