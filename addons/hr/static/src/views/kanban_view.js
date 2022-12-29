/** @odoo-module */

import { registry } from '@web/core/registry';

import { kanbanView } from '@web/views/kanban/kanban_view';
import { KanbanModel } from '@web/views/kanban/kanban_model';

export class EmployeeKanbanRecord extends KanbanModel.Record {
    async openChat(employeeId) {
        this.model.env.services["mail.messaging"].openChat({ employeeId });
    }
}

export class EmployeeKanbanModel extends KanbanModel {}

EmployeeKanbanModel.services = [...KanbanModel.services, "mail.messaging"];
EmployeeKanbanModel.Record = EmployeeKanbanRecord;

registry.category('views').add('hr_employee_kanban', {
    ...kanbanView,
    Model: EmployeeKanbanModel,
});
