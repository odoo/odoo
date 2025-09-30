import { registry } from "@web/core/registry";

import { kanbanView } from "@web/views/kanban/kanban_view";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { HrActionMenus } from "../search/hr_action_menus/hr_action_menus";
import { HrEmployeeActionHelper } from "@hr/views/hr_employee_action_helper/hr_employee_action_helper";

export class HrEmployeeKanbanRenderer extends KanbanRenderer {
    static components = {
        ...KanbanRenderer.components,
        ActionHelper: HrEmployeeActionHelper,
    };
}

export class HrEmployeeKanbanController extends KanbanController {
    static components = {
        ...KanbanController.components,
        ActionMenus: HrActionMenus,
    };
}

registry.category("views").add("hr_employee_kanban", {
    ...kanbanView,
    Controller: HrEmployeeKanbanController,
    Renderer: HrEmployeeKanbanRenderer,
});
