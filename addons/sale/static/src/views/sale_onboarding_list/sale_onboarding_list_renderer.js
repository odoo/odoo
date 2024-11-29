import { FileUploadListRenderer } from "@account/views/file_upload_list/file_upload_list_renderer";
import { SaleActionHelper } from "../../js/sale_action_helper/sale_action_helper";

export class SaleListRenderer extends FileUploadListRenderer {
    static template = "sale.SaleListRenderer";
    static components = {
        ...FileUploadListRenderer.components,
        SaleActionHelper,
    };
};
