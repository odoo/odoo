import { SaleKanbanRenderer } from "./sale_onboarding_kanban_renderer";
import { fileUploadKanbanView } from "@account/views/file_upload_kanban/file_upload_kanban_view";
import { registry } from "@web/core/registry";

export const saleKanbanView = {
    ...fileUploadKanbanView,
    Renderer: SaleKanbanRenderer,
};

registry.category("views").add("sale_onboarding_kanban", saleKanbanView);
