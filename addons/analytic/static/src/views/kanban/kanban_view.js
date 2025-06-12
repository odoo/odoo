import { registry } from "@web/core/registry";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { AnalyticSearchModel } from "@analytic/views/analytic_search_model";

export const analyticKanbanView = {
    ...kanbanView,
    SearchModel: AnalyticSearchModel,
};

registry.category("views").add("analytic_kanban", analyticKanbanView);
