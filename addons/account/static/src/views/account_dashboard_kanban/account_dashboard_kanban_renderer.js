import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { AccountDashboardKpis } from "@account/components/account_dashboard_kpis/account_dashboard_kpis";
import { DashboardKanbanRecord } from "./account_dashboard_kanban_record";

export class DashboardKanbanRenderer extends KanbanRenderer {
    static template = "account.DashboardKanbanRenderer";
    static components = {
        ...KanbanRenderer.components,
        KanbanRecord: DashboardKanbanRecord,
        AccountDashboardKpis,
    };
}
