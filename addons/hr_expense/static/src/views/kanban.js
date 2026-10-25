import { registry } from '@web/core/registry';

import { ExpenseDashboard } from '../components/expense_dashboard';
import { ExpenseMobileQRCode } from '../mixins/qrcode';
import { ExpenseDocumentUpload, ExpenseDocumentDropZone } from '../mixins/document_upload';
import { ExpenseActionsUtil } from "./expense_actions_util";

import { kanbanView } from '@web/views/kanban/kanban_view';
import { KanbanController } from '@web/views/kanban/kanban_controller';
import { KanbanRenderer } from '@web/views/kanban/kanban_renderer';
import { onWillStart } from "@odoo/owl";

export class ExpenseKanbanController extends ExpenseDocumentUpload(KanbanController) {
    static template = "hr_expense.KanbanView";

    setup() {
        super.setup();
        this.actionsHelper = new ExpenseActionsUtil(this);
        onWillStart(this.actionsHelper.onWillStartUtil);
    }

    async onClick (action) {
        await this.actionsHelper.onClick(action);
    }

    getStaticActionMenuItems() {
        const menuItems = super.getStaticActionMenuItems(...arguments);
        return {
            ...menuItems,
            ...this.actionsHelper.getExtraStaticActionMenuItems(),
        }
    }
}

export class ExpenseKanbanRenderer extends ExpenseDocumentDropZone(
    ExpenseMobileQRCode(KanbanRenderer)
) {
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
});

registry.category('views').add('hr_expense_dashboard_kanban', {
    ...kanbanView,
    Controller: ExpenseKanbanController,
    Renderer: ExpenseDashboardKanbanRenderer,
});
