import { registry } from "@web/core/registry";
import { PurchaseDashBoard } from "@purchase/views/purchase_dashboard";
import { PurchaseFileUploader } from "@purchase/components/purchase_file_uploader/purchase_file_uploader";
import { FileUploadListController } from "@account/views/file_upload_list/file_upload_list_controller";
import { FileUploadListRenderer } from "@account/views/file_upload_list/file_upload_list_renderer";
import { fileUploadListView } from "@account/views/file_upload_list/file_upload_list_view";

export class PurchaseDashBoardRenderer extends FileUploadListRenderer {
    static template = "purchase.ListRenderer";
    static components = Object.assign({}, FileUploadListRenderer.components, { PurchaseDashBoard });
}

export class PurchaseFileUploadListController extends FileUploadListController {
    static template = `purchase.ListView`;
    static components = {
        ...FileUploadListController.components,
        PurchaseFileUploader,
    };
}

export const PurchaseDashBoardListView = {
    ...fileUploadListView,
    Controller: PurchaseFileUploadListController,
    Renderer: PurchaseDashBoardRenderer,
};

registry.category("views").add("purchase_dashboard_list", PurchaseDashBoardListView);
