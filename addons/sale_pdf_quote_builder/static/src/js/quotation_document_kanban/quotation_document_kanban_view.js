import {
    productDocumentKanbanView
} from '@product/js/product_document_kanban/product_document_kanban_view';
import {
    QuotationDocumentKanbanController
} from '@sale_pdf_quote_builder/js/quotation_document_kanban/quotation_document_kanban_controller';
import { registry } from '@web/core/registry';

export const quotationDocumentKanbanView = {
    ...productDocumentKanbanView,
    Controller: QuotationDocumentKanbanController,
};

registry.category('views').add('quotation_document_kanban', quotationDocumentKanbanView);
