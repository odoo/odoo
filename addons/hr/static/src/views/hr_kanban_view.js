import { registry } from "@web/core/registry";

import { kanbanView } from "@web/views/kanban/kanban_view";
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { HrActionMenus } from "../search/hr_action_menus/hr_action_menus";

export class HrEmployeeKanbanController extends KanbanController {
    static components = {
        ...KanbanController.components,
        ActionMenus: HrActionMenus,
    };
}

registry.category("views").add("hr_employee_kanban", {
    ...kanbanView,
    Controller: HrEmployeeKanbanController,
});
