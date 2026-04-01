import { registry } from "@web/core/registry";

import { kanbanView } from "@web/views/kanban/kanban_view";
import { KanbanController } from "@web/views/kanban/kanban_controller";

import { useArchiveEmployee } from "@hr/views/archive_employee_hook";

export class EmployeeKanbanController extends KanbanController {
    setup() {
        super.setup();
        this.archiveEmployee = useArchiveEmployee();
    }

    getStaticActionMenuItems() {
        const menuItems = super.getStaticActionMenuItems();
        const selectedRecords = this.model.root.selection;

        menuItems.archive.callback = this.archiveEmployee.bind(
            this,
            selectedRecords.map(({ resId }) => resId)
        );
        return menuItems;
    }
}

registry.category("views").add("hr_employee_kanban", {
    ...kanbanView,
    Controller: EmployeeKanbanController,
});
