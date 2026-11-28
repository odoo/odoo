import { ExpenseDashboard } from '../components/expense_dashboard';
import { ExpenseMobileQRCode } from '../mixins/qrcode';
import { ExpenseDocumentDropZone } from '../mixins/document_upload';
import { ExpenseCollectionAction } from "../mixins/expense_collection_action";

import { registry } from '@web/core/registry';
import { listView } from "@web/views/list/list_view";

import { ListController } from "@web/views/list/list_controller";
import { ListRenderer } from "@web/views/list/list_renderer";

export class ExpenseListController extends ExpenseCollectionAction(ListController) {
    static template = `hr_expense.ListView`;
}

export class ExpenseListRenderer extends ExpenseDocumentDropZone(
    ExpenseMobileQRCode(ListRenderer)
) {
    static template = "hr_expense.ListRenderer";
}

export class ExpenseDashboardListRenderer extends ExpenseListRenderer {
    static components = { ...ExpenseDashboardListRenderer.components, ExpenseDashboard };
    static template = "hr_expense.DashboardListRenderer";
}

registry.category('views').add('hr_expense_tree', {
    ...listView,
    buttonTemplate: 'hr_expense.ListButtons',
    Controller: ExpenseListController,
    Renderer: ExpenseListRenderer,
});

registry.category('views').add('hr_expense_dashboard_tree', {
    ...listView,
    buttonTemplate: 'hr_expense.ListButtons',
    Controller: ExpenseListController,
    Renderer: ExpenseDashboardListRenderer,
});
