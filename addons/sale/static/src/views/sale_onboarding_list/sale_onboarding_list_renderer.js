import { SaleFileUploadListRenderer } from '../sale_file_upload_list/sale_file_upload_list_renderer';
import { SaleActionHelper } from "../../js/sale_action_helper/sale_action_helper";

export class SaleListRenderer extends SaleFileUploadListRenderer {
    static template = "sale.SaleListRenderer";
    static components = {
        ...SaleFileUploadListRenderer.components,
        SaleActionHelper,
    };
};
