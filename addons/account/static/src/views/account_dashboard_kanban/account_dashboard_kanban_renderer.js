import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { AccountDashboardKpis } from "@account/components/account_dashboard_kpis/account_dashboard_kpis";

export class DashboardKanbanRenderer extends KanbanRenderer {
    static template = "account.DashboardKanbanRenderer";
    static components = {
        ...KanbanRenderer.components,
        AccountDashboardKpis,
    };
}
