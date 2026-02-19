import { registry } from "@web/core/registry";
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { HrPresenceActionMenus } from "../search/hr_presence_action_menus/hr_presence_action_menus";
import { employeeKanbanView } from "@hr/views/hr_employee_kanban_view";

export class EmployeeKanbanController extends KanbanController {
    static components = {
        ...KanbanController.components,
        ActionMenus: HrPresenceActionMenus,
    };
}

registry.category("views").add("hr_presence_employee_kanban", {
    ...employeeKanbanView,
    Controller: EmployeeKanbanController,
});
