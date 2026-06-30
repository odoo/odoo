import {
    ProductDocumentKanbanRenderer
} from "@product/js/product_document_kanban/product_document_kanban_renderer";
import { UploadButton } from '@product/js/product_document_kanban/upload_button/upload_button';
import { registry } from '@web/core/registry';
import { X2ManyField, x2ManyField } from '@web/views/fields/x2many/x2many_field';

export class QuotationDocumentX2ManyField extends X2ManyField {
    static template = 'sale_pdf_quote_builder.QuotationDocumentX2ManyField';
    static components = {
        ...X2ManyField.components,
        UploadButton,
        KanbanRenderer: ProductDocumentKanbanRenderer,
    };

    setup() {
        super.setup();
        this.uploadRoute = '/sale_pdf_quote_builder/quotation_document/upload';
        this.formData = {
            'sale_order_template_id': this.props.record.resId,
        };
        this.allowedMIMETypes='application/pdf';
    }
}

export const quotationDocumentX2ManyField = {
    ...x2ManyField,
    component: QuotationDocumentX2ManyField,
};

registry.category('fields').add('quotation_document_many2many', quotationDocumentX2ManyField);
