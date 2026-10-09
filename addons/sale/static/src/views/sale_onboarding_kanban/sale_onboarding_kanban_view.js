import { registry } from "@web/core/registry";
import { saleFileUploadKanbanView } from "../sale_file_upload_kanban/sale_file_upload_kanban_view";

export const saleKanbanView = {
    ...saleFileUploadKanbanView,
};

registry.category("views").add("sale_onboarding_kanban", saleKanbanView);
