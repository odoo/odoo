/** @odoo-module */

import { registry } from '@web/core/registry';
import { patch } from '@web/core/utils/patch';

import { kanbanView } from '@web/views/kanban/kanban_view';
import { KanbanModel } from '@web/views/kanban/kanban_model';

import { EmployeeChatMixin } from '../mixins/chat_mixin';

export class EmployeeKanbanRecord extends KanbanModel.Record {}
patch(EmployeeKanbanRecord.prototype, 'employee_kanban_record_mixin', EmployeeChatMixin);

export class EmployeeKanbanModel extends KanbanModel {}
EmployeeKanbanModel.Record = EmployeeKanbanRecord;

registry.category('views').add('hr_employee_kanban', {
    ...kanbanView,
    Model: EmployeeKanbanModel,
});
