import { registry } from "@web/core/registry";

import { kanbanView } from "@web/views/kanban/kanban_view";
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { KanbanRecord } from "@web/views/kanban/kanban_record";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";

import { useArchiveEmployee } from "@hr/views/archive_employee_hook";
import { patchHrEmployee } from "./patch_hr_employee";

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

export class HrKanbanRecord extends KanbanRecord {
    static template = "hr.KanbanRecord";
    static props = [...KanbanRecord.props, "showActionHelper"];
}

export class EmployeeKanbanRenderer extends KanbanRenderer {
    static template = "hr.KanbanRenderer";
    static components = {
        ...KanbanRenderer.components,
        KanbanRecord: HrKanbanRecord,
    };
}
patchHrEmployee(EmployeeKanbanRenderer);

registry.category("views").add("hr_employee_kanban", {
    ...kanbanView,
    Controller: EmployeeKanbanController,
    Renderer: EmployeeKanbanRenderer,
});
