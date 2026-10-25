import { FileUploadListController } from "../file_upload_list/file_upload_list_controller";
import { AccountFileUploader } from "../../components/account_file_uploader/account_file_uploader";

export class AccountUploadListController extends FileUploadListController {
    static components = {
        ...FileUploadListController.components,
        AccountFileUploader,
    };
}
