import { registry } from "@web/core/registry";
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { kanbanView } from "@web/views/kanban/kanban_view";

export class EmployeeKanbanController extends KanbanController {

    getStaticActionMenuItems() {
        const menuItems = super.getStaticActionMenuItems();
        delete menuItems.delete;
        return menuItems;
    }
}

registry.category("views").add("hr_employee_kanban_action", {
    ...kanbanView,
    Controller: EmployeeKanbanController,
});
