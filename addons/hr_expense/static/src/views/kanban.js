/** @odoo-module */

import { registry } from '@web/core/registry';

import { ExpenseDashboard } from '../components/expense_dashboard';
import { ExpenseMobileQRCode } from '../mixins/qrcode';
import { ExpenseDocumentUpload, ExpenseDocumentDropZone } from '../mixins/document_upload';

import { kanbanView } from '@web/views/kanban/kanban_view';
import { KanbanController } from '@web/views/kanban/kanban_controller';
import { KanbanRenderer } from '@web/views/kanban/kanban_renderer';

export class ExpenseKanbanController extends ExpenseDocumentUpload(KanbanController) {}
ExpenseKanbanController.template = "hr_expense.KanbanView";

export class ExpenseKanbanRenderer extends ExpenseDocumentDropZone(ExpenseMobileQRCode(KanbanRenderer)) {}
ExpenseKanbanRenderer.template = 'hr_expense.KanbanRenderer';

export class ExpenseDashboardKanbanRenderer extends ExpenseKanbanRenderer {}
ExpenseDashboardKanbanRenderer.components = { ...ExpenseDashboardKanbanRenderer.components, ExpenseDashboard};
ExpenseDashboardKanbanRenderer.template = 'hr_expense.DashboardKanbanRenderer';

registry.category('views').add('hr_expense_kanban', {
    ...kanbanView,
    Controller: ExpenseKanbanController,
    Renderer: ExpenseKanbanRenderer,
});

registry.category('views').add('hr_expense_dashboard_kanban', {
    ...kanbanView,
    Controller: ExpenseKanbanController,
    Renderer: ExpenseDashboardKanbanRenderer,
});
