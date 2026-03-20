import { FileUploadKanbanController } from '@account/views/file_upload_kanban/file_upload_kanban_controller';

export class SaleFileUploadKanbanController extends FileUploadKanbanController {
    setup() {
        super.setup();
        this.hideUploadButton = true;
    }
};
