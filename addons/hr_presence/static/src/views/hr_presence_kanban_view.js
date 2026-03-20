import { registry } from "@web/core/registry";

import { kanbanView } from "@web/views/kanban/kanban_view";
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { HrPresenceActionMenus } from "../search/hr_presence_action_menus/hr_presence_action_menus";

export class EmployeeKanbanController extends KanbanController {
    static components = {
        ...KanbanController.components,
        ActionMenus: HrPresenceActionMenus,
    };
}

registry.category("views").add("hr_employee_kanban", {
    ...kanbanView,
    Controller: EmployeeKanbanController,
});
