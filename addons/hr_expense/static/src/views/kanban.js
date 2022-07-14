/** @odoo-module */

import { registry } from '@web/core/registry';
import { patch } from '@web/core/utils/patch';

import { ExpenseDashboardMixin } from '../mixins/expense_dashboard';
import { ExpenseMobileQRCode } from '../mixins/qrcode';
import { ExpenseDocumentUpload } from '../mixins/document_upload';

import { kanbanView } from '@web/views/kanban/kanban_view';
import { KanbanController } from '@web/views/kanban/kanban_controller';
import { KanbanRenderer } from '@web/views/kanban/kanban_renderer';

export class ExpenseKanbanController extends KanbanController {}
patch(ExpenseKanbanController.prototype, 'expense_kanban_controller_upload', ExpenseDocumentUpload);

export class ExpenseKanbanRenderer extends KanbanRenderer {}
patch(ExpenseKanbanRenderer.prototype, 'expense_kanban_renderer_qrcode', ExpenseMobileQRCode);

export class ExpenseDashboardKanbanRenderer extends ExpenseKanbanRenderer {}
patch(ExpenseDashboardKanbanRenderer.prototype, 'expense_kanban_renderer_dashboard', ExpenseDashboardMixin);
ExpenseDashboardKanbanRenderer.template = 'hr_expense.KanbanRenderer';

registry.category('views').add('hr_expense_kanban', {
    ...kanbanView,
    buttonTemplate: 'hr_expense.KanbanButtons',
    Controller: ExpenseKanbanController,
    Renderer: ExpenseKanbanRenderer,
});

registry.category('views').add('hr_expense_dashboard_kanban', {
    ...kanbanView,
    buttonTemplate: 'hr_expense.KanbanButtons',
    Controller: ExpenseKanbanController,
    Renderer: ExpenseDashboardKanbanRenderer,
});
