import { QuotationDocumentKanbanController } from '@sale_pdf_quote_builder/js/quotation_document_kanban/quotation_document_kanban_controller';
import { registry } from '@web/core/registry';
import { kanbanView } from '@web/views/kanban/kanban_view';

export const quotationDocumentKanbanView = {
    ...kanbanView,
    Controller: QuotationDocumentKanbanController,
    buttonTemplate: 'sale_pdf_quote_builder.QuotationDocumentKanbanView.Buttons',
};

registry.category('views').add('quotation_document_kanban', quotationDocumentKanbanView);
