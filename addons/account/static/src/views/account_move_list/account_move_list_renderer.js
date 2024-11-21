import { BillGuide } from "@account/components/bill_guide/bill_guide";
import { FileUploadListRenderer } from "../file_upload_list/file_upload_list_renderer";

export class AccountMoveUploadListRenderer extends FileUploadListRenderer {
    static template = "account.AccountMoveListRenderer";
    static components = {
        ...FileUploadListRenderer.components,
        BillGuide,
    };
}
