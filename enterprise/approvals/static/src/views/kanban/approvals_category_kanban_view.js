import { registry } from "@web/core/registry";
import { kanbanView } from "@web/views/kanban/kanban_view";

import { ApprovalKanbanRenderer, ApprovalCategoryKanbanController } from "./approvals_category_kanban_controller";

export const approvalsCategoryKanbanView = {
    ...kanbanView,
    Controller: ApprovalCategoryKanbanController,
    Renderer: ApprovalKanbanRenderer,
    buttonTemplate: "approvals.ApprovalsCategoryKanbanView.Buttons",
};

registry.category("views").add("approvals_category_kanban", approvalsCategoryKanbanView);
