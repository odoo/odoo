import { registry } from "@web/core/registry";
import { PurchaseDashBoard } from "@purchase/views/purchase_dashboard";
import { FileUploadListRenderer } from "@account/views/file_upload_list/file_upload_list_renderer";
import { fileUploadListView } from "@account/views/file_upload_list/file_upload_list_view";

export class PurchaseDashBoardRenderer extends FileUploadListRenderer {
    static template = "purchase.PurchaseListView";
    static components = Object.assign({}, FileUploadListRenderer.components, { PurchaseDashBoard });
}

export const PurchaseDashBoardListView = {
    ...fileUploadListView,
    Renderer: PurchaseDashBoardRenderer,
};

registry.category("views").add("purchase_dashboard_list", PurchaseDashBoardListView);
