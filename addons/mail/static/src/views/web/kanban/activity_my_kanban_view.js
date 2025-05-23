import { kanbanView } from "@web/views/kanban/kanban_view";
import { ActivityMyKanbanController } from "./activity_my_kanban_controller";
import { registry } from "@web/core/registry";

export const activityMyKanbanView = {
    ...kanbanView,
    Controller: ActivityMyKanbanController,
};

registry.category("views").add("activity_my_kanban", activityMyKanbanView);
