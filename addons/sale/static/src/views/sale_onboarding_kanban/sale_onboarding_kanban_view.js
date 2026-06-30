import { registry } from "@web/core/registry";
import { saleFileUploadKanbanView } from "../sale_file_upload_kanban/sale_file_upload_kanban_view";
import { SaleKanbanRenderer } from "./sale_onboarding_kanban_renderer";

export const saleKanbanView = {
    ...saleFileUploadKanbanView,
    Renderer: SaleKanbanRenderer,
};

registry.category("views").add("sale_onboarding_kanban", saleKanbanView);
