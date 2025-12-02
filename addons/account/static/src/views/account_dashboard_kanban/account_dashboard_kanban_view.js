import { registry } from "@web/core/registry";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { DashboardKanbanRenderer } from "./account_dashboard_kanban_renderer";

export const accountDashboardKanbanView = {
    ...kanbanView,
    Renderer: DashboardKanbanRenderer,
};

registry.category("views").add("account_dashboard_kanban", accountDashboardKanbanView);
