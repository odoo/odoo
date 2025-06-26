import { ListController } from "@web/views/list/list_controller";
import { DocumentFileUploader } from "@account/components/document_file_uploader/document_file_uploader";

export class FileUploadListController extends ListController {
    static components = {
        ...ListController.components,
        DocumentFileUploader,
    };
};
