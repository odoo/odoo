import { registry } from "@web/core/registry";
import { saleOrderKanbanView } from "../sale_order_kanban/sale_order_kanban_view";

export const saleKanbanView = {
    ...saleOrderKanbanView,
};

registry.category("views").add("sale_onboarding_kanban", saleKanbanView);
