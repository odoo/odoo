import {
    QuotationDocumentListController
} from '@sale_pdf_quote_builder/js/quotation_document_list/quotation_document_list_controller';
import { registry } from '@web/core/registry';
import { listView } from '@web/views/list/list_view';

export const quotationDocumentListView = {
    ...listView,
    Controller: QuotationDocumentListController,
};

registry.category('views').add('quotation_document_list', quotationDocumentListView);
