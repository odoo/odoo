import { FileUploadListController } from '@account/views/file_upload_list/file_upload_list_controller';

export class SaleFileUploadListController extends FileUploadListController {
    setup() {
        super.setup();
        this.hideUploadButton = true;
    }
};
