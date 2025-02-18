import { registry } from "@web/core/registry";
import { fileUploadKanbanView } from "@account/views/file_upload_kanban/file_upload_kanban_view";
import { FileUploadKanbanRenderer } from "@account/views/file_upload_kanban/file_upload_kanban_renderer";
import { PurchaseDashBoard } from "@purchase/views/purchase_dashboard";

export class PurchaseDashBoardKanbanRenderer extends FileUploadKanbanRenderer {
    static template = "purchase.PurchaseKanbanView";
    static components = Object.assign({}, FileUploadKanbanRenderer.components, { PurchaseDashBoard });
}

export const PurchaseDashBoardKanbanView = {
    ...fileUploadKanbanView,
    Renderer: PurchaseDashBoardKanbanRenderer,
};

registry.category("views").add("purchase_dashboard_kanban", PurchaseDashBoardKanbanView);
