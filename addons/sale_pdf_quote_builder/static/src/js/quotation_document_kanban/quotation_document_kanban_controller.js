import { KanbanController } from '@web/views/kanban/kanban_controller';
import { useBus, useService } from '@web/core/utils/hooks';
import { useRef } from '@odoo/owl';

export class QuotationDocumentKanbanController extends KanbanController {
    setup() {
        super.setup();
        this.uploadFileInputRef = useRef('uploadFileInput');
        this.fileUploadService = useService('file_upload');
        useBus(
            this.fileUploadService.bus,
            'FILE_UPLOAD_LOADED',
            async () => {
                await this.model.root.load();
            },
        );
    }

    async onFileInputChange(ev) {
        if (!ev.target.files.length) {
            return;
        }
        await this.fileUploadService.upload(
            '/sale_pdf_quote_builder/quotation_document/upload',
            ev.target.files,
        );
        // Reset the file input's value so that the same file may be uploaded twice.
        ev.target.value = '';
    }

}
