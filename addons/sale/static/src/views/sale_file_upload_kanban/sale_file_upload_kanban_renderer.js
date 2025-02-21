import { _t } from '@web/core/l10n/translation';
import { FileUploadKanbanRenderer } from '@account/views/file_upload_kanban/file_upload_kanban_renderer';

export class SaleFileUploadKanbanRenderer extends FileUploadKanbanRenderer {
    setup() {
        super.setup();
        this.dropZoneTitle = _t("Import a request for quotation from a customer");
        this.dropZoneDescription = _t(`
            If your customer runs on Odoo 18 or higher, customer data and sales order lines
            will be automatically created. Any other pdf containing an attached
            UBL-RequestForQuotation file will work as well.
        `);
    }
}
