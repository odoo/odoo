import { _t } from '@web/core/l10n/translation';
import { markup } from '@odoo/owl';
import { FileUploadKanbanRenderer } from '@account/views/file_upload_kanban/file_upload_kanban_renderer';

export class SaleFileUploadKanbanRenderer extends FileUploadKanbanRenderer {
    setup() {
        super.setup();
        const title = _t("Import a request for quotation from a customer");
        const description = _t(`
            If your customer runs on Odoo 18 or higher,customer data and sales order lines
            will be automatically created. Any other pdf containing an attached
            UBL-RequestForQuotation file will work as well.
        `);
        this.dropZoneHelper = markup(`
            <h2 class="mt-4 text-white fw-bold">${title}</h2>
            <span class="mt-4 text-white fw-bold">${description}</span>
        `);
    }
}
