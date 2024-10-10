/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { KanbanController } from '@web/views/kanban/kanban_controller';
import { patch } from "@web/core/utils/patch";
import { UploadButton } from '@product/js/product_document_kanban/upload_button/upload_button';
import { useService } from '@web/core/utils/hooks';

export class QuotationDocumentKanbanController extends KanbanController {
    static components = { ...KanbanController.components, UploadButton };

    setup() {
        super.setup();
        this.uploadRoute = '/sale_pdf_quote_builder/quotation_document/upload';
    }
}

patch(UploadButton.prototype, {
    setup() {
        super.setup();
        this.notification = useService('notification');
    },
    async onFileInputChange(ev) {
        if ([...ev.target.files].some(file => !file.name.endsWith('.pdf'))) {
            this.notification.add(_t('Only PDF documents can be used as header or footer.'), {
                type: "danger",
            });
            return;
        }
        super.onFileInputChange(ev)
    },
});
