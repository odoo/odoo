import {
    ProductDocumentKanbanRenderer
} from "@product/js/product_document_kanban/product_document_kanban_renderer";
import { registry } from '@web/core/registry';
import { X2ManyField, x2ManyField } from '@web/views/fields/x2many/x2many_field';

export class QuotationDocumentX2ManyField extends X2ManyField {
    static components = {
        ...X2ManyField.components,
        KanbanRenderer: ProductDocumentKanbanRenderer,
    };
}

export const quotationDocumentX2ManyField = {
    ...x2ManyField,
    component: QuotationDocumentX2ManyField,
};

registry.category('fields').add('quotation_document_many2many', quotationDocumentX2ManyField);
