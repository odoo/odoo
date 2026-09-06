import { UploadButton } from '@product/js/product_document_kanban/upload_button/upload_button';
import { ListController } from '@web/views/list/list_controller';
import { FormViewDialog } from '@web/views/view_dialogs/form_view_dialog';

export class QuotationDocumentListController extends ListController {
    static template = 'sale_pdf_quote_builder.QuotationDocumentListView';
    static components = { ...ListController.components, UploadButton };

    setup() {
        super.setup();
        this.uploadRoute = '/sale_pdf_quote_builder/quotation_document/upload';
        this.allowedMIMETypes='application/pdf';
    }

    get formData() {
        const allowedCompanyIds = this.props.context.allowed_company_ids;
        return allowedCompanyIds
            ? { allowed_company_ids: JSON.stringify(allowedCompanyIds) }
            : {};
    }

    /**
     * @override
     *
     * Override to create the record in a dialog, as the list can't switch to the form view when
     * it is itself displayed in a dialog. The list is reloaded afterwards to let the new document
     * be selected right away.
     */
    async createRecord(params) {
        if (!this.env.inDialog) {
            return super.createRecord(params);
        }
        this.dialogService.add(FormViewDialog, {
            resModel: this.props.resModel,
            context: this.props.context,
            onRecordSaved: () => this.model.root.load(),
        });
    }
}
