/** @odoo-module **/

import { registry } from "@web/core/registry";

import { kanbanView } from "@web/views/kanban/kanban_view";
import { QuotationDocumentKanbanController } from "@sale_pdf_quote_builder/js/quotation_document_kanban/quotation_document_kanban_controller";
import { QuotationDocumentKanbanRenderer } from "@sale_pdf_quote_builder/js/quotation_document_kanban/quotation_document_kanban_renderer";

export const quotationDocumentKanbanView = {
    ...kanbanView,
    Controller: QuotationDocumentKanbanController,
    Renderer: QuotationDocumentKanbanRenderer,
    buttonTemplate: "sale_pdf_quote_builder.QuotationDocumentKanbanView.Buttons",
};

registry.category("views").add("quotation_document_kanban", quotationDocumentKanbanView);
