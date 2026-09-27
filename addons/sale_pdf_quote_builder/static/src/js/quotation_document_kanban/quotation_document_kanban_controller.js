import { UploadButton } from '@product/js/product_document_kanban/upload_button/upload_button';
import { KanbanController } from '@web/views/kanban/kanban_controller';

export class QuotationDocumentKanbanController extends KanbanController {
    static components = { ...KanbanController.components, UploadButton };

    setup() {
        super.setup();
        this.uploadRoute = '/sale_pdf_quote_builder/quotation_document/upload';
        this.allowedMIMETypes='application/pdf';
    }

    get formData() {
        return {
            allowed_company_ids: JSON.stringify(this.props.context.allowed_company_ids),
        };
    }
}
