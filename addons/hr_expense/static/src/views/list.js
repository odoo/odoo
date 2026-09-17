import { ExpenseDashboard } from '../components/expense_dashboard';
import { ExpenseMobileQRCode } from '../mixins/qrcode';
import { ExpenseDocumentUpload, ExpenseDocumentDropZone } from '../mixins/document_upload';
import { ExpenseActionsUtil } from "./expense_actions_util";

import { registry } from '@web/core/registry';
import { listView } from "@web/views/list/list_view";

import { ListController } from "@web/views/list/list_controller";
import { ListRenderer } from "@web/views/list/list_renderer";
import { onWillStart } from "@odoo/owl";

export class ExpenseListController extends ExpenseDocumentUpload(ListController) {
    static template = `hr_expense.ListView`;

    setup() {
        super.setup();
        this.actionsHelper = new ExpenseActionsUtil(this);
        onWillStart(this.actionsHelper.onWillStartUtil);
    }

    displaySubmit() {
        return this.actionsHelper.display('action_submit');
    }

    displayApprove() {
        return this.actionsHelper.display('action_approve');
    }

    displayPost() {
        return this.actionsHelper.display('action_post');
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
