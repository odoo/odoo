import { useSubEnv } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { HrEmployeeActionHelper } from "@hr/views/hr_employee_action_helper/hr_employee_action_helper";

export class HrEmployeeKanbanRenderer extends KanbanRenderer {
    static components = {
        ...KanbanRenderer.components,
        ActionHelper: HrEmployeeActionHelper,
    };

    setup() {
        super.setup();
        const getEmployeesCount = this._getEmployeesCount.bind(this);
        useSubEnv({
            getEmployeesCount: getEmployeesCount,
        });
    }

    _getEmployeesCount() {
        if (this.props.list.model.useSampleModel) {
            return 0;
        }
        return this.env.model.root.records.length;
    }
}

export const employeeKanbanView = {
    ...kanbanView,
    Renderer: HrEmployeeKanbanRenderer,
};
registry.category("views").add("hr_employee_kanban", employeeKanbanView);
