import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ListRenderer } from "@web/views/list/list_renderer";
import { ListController } from "@web/views/list/list_controller";
import { PurchaseDashBoard } from "@purchase/views/purchase_dashboard";
import { PurchaseFileUploader } from "@purchase/components/purchase_file_uploader/purchase_file_uploader";

export class PurchaseDashBoardRenderer extends ListRenderer {
    static template = "purchase.ListRenderer";
    static components = Object.assign({}, ListRenderer.components, { PurchaseDashBoard });
}

export class FileUploadListController extends ListController {
    static template = `purchase.ListView`;
    static components = {
        ...ListController.components,
        PurchaseFileUploader,
    };
}

export const PurchaseDashBoardListView = {
    ...listView,
    Controller: FileUploadListController,
    Renderer: PurchaseDashBoardRenderer,
};

registry.category("views").add("purchase_dashboard_list", PurchaseDashBoardListView);
