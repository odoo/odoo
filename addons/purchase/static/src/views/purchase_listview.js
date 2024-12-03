import { registry } from "@web/core/registry";
import { ListRenderer } from "@web/views/list/list_renderer";
import { PurchaseDashBoard } from "@purchase/views/purchase_dashboard";
import { FileUploadListRenderer } from "@account/views/file_upload_list/file_upload_list_renderer";
import { fileUploadListView } from "@account/views/file_upload_list/file_upload_list_view";

export class PurchaseDashBoardRenderer extends ListRenderer {
    static template = "purchase.PurchaseListView";
    static components = Object.assign({}, ListRenderer.components, { PurchaseDashBoard, FileUploadListRenderer });
}

export const PurchaseDashBoardListView = {
    ...fileUploadListView,
    Renderer: PurchaseDashBoardRenderer,
};

registry.category("views").add("purchase_dashboard_list", PurchaseDashBoardListView);
