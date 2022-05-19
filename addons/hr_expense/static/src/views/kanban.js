/** @odoo-module */

import { registry } from '@web/core/registry';
import { patch } from '@web/core/utils/patch';

import { ExpenseDashboard } from '../components/expense_dashboard';
import { ExpenseMobileQRCode } from '../mixins/qrcode';
import { ExpenseDocumentUpload, ExpenseDocumentDropZone } from '../mixins/document_upload';

import { kanbanView } from '@web/views/kanban/kanban_view';
import { KanbanController } from '@web/views/kanban/kanban_controller';
import { KanbanRenderer } from '@web/views/kanban/kanban_renderer';

export class ExpenseKanbanController extends KanbanController {}
patch(ExpenseKanbanController.prototype, 'expense_kanban_controller_upload', ExpenseDocumentUpload);

export class ExpenseKanbanRenderer extends KanbanRenderer {}
patch(ExpenseKanbanRenderer.prototype, 'expense_kanban_renderer_qrcode', ExpenseMobileQRCode);
patch(ExpenseKanbanRenderer.prototype, 'expense_kanban_renderer_qrcode_dzone', ExpenseDocumentDropZone);
ExpenseKanbanRenderer.template = 'hr_expense.KanbanRenderer';

export class ExpenseDashboardKanbanRenderer extends ExpenseKanbanRenderer {}
ExpenseDashboardKanbanRenderer.components = { ...ExpenseDashboardKanbanRenderer.components, ExpenseDashboard};
ExpenseDashboardKanbanRenderer.template = 'hr_expense.DashboardKanbanRenderer';

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
