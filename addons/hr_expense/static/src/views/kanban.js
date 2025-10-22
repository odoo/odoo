import { registry } from '@web/core/registry';

import { ExpenseDashboard } from "@hr_expense/components/expense_dashboard";
import { ExpenseDocumentUpload, ExpenseDocumentDropZone } from "@hr_expense/mixins/document_upload";

import { kanbanView } from '@web/views/kanban/kanban_view';
import { KanbanController } from '@web/views/kanban/kanban_controller';
import { KanbanRenderer } from '@web/views/kanban/kanban_renderer';

export class ExpenseKanbanController extends ExpenseDocumentUpload(KanbanController) {
    static template = "hr_expense.KanbanView";
}

export class ExpenseKanbanRenderer extends ExpenseDocumentDropZone(KanbanRenderer) {
    static template = "hr_expense.KanbanRenderer";
}

export class ExpenseDashboardKanbanRenderer extends ExpenseKanbanRenderer {
    static components = { ...ExpenseDashboardKanbanRenderer.components, ExpenseDashboard };
    static template = "hr_expense.DashboardKanbanRenderer";
}

registry.category('views').add('hr_expense_kanban', {
    ...kanbanView,
    Controller: ExpenseKanbanController,
    Renderer: ExpenseKanbanRenderer,
    buttonTemplate: "hr_expense.KanbanView.Buttons"
});

registry.category('views').add('hr_expense_dashboard_kanban', {
    ...kanbanView,
    Controller: ExpenseKanbanController,
    Renderer: ExpenseDashboardKanbanRenderer,
    buttonTemplate: "hr_expense.KanbanView.Buttons"
});
