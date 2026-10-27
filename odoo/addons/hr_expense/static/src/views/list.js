/** @odoo-module */

import { ExpenseDashboard } from '../components/expense_dashboard';
import { ExpenseMobileQRCode } from '../mixins/qrcode';
import { ExpenseDocumentUpload, ExpenseDocumentDropZone } from '../mixins/document_upload';

import { registry } from '@web/core/registry';
import { useService } from '@web/core/utils/hooks';
import { listView } from "@web/views/list/list_view";

import { ListController } from "@web/views/list/list_controller";
import { ListRenderer } from "@web/views/list/list_renderer";
import { onWillStart } from "@odoo/owl";

export class ExpenseListController extends ExpenseDocumentUpload(ListController) {
    setup() {
        super.setup();
        this.orm = useService('orm');
        this.actionService = useService('action');
        this.rpc = useService("rpc");
        this.user = useService("user");
        this.isExpenseSheet = this.model.config.resModel === "hr.expense.sheet";

        onWillStart(async () => {
            this.userIsExpenseTeamApprover = await this.user.hasGroup("hr_expense.group_hr_expense_team_approver");
            this.userIsAccountInvoicing = await this.user.hasGroup("account.group_account_invoice");
        });
    }

    displaySubmit() {
        const records = this.model.root.selection;
        return records.length && records.every(record => record.data.state === 'draft') && this.isExpenseSheet;
    }

    displayApprove() {
        const records = this.model.root.selection;
        return this.userIsExpenseTeamApprover && records.length && records.every(record => record.data.state === 'submit') && this.isExpenseSheet;
    }

    displayPost() {
        const records = this.model.root.selection;
        return this.userIsAccountInvoicing && records.length && records.every(record => record.data.state === 'approve') && this.isExpenseSheet;
    }

    displayPayment() {
        const records = this.model.root.selection;
        return this.userIsAccountInvoicing && records.length && records.every(record => record.data.state === 'post' && record.data.payment_state === 'not_paid') && this.isExpenseSheet;
    }

    async onClick (action) {
        const records = this.model.root.selection;
        const recordIds = records.map((a) => a.resId);
        const model = this.model.config.resModel;
        const context = {};
        if (action === 'action_approve_expense_sheets') {
            context['validate_analytic'] = true;
        }
        const res = await this.orm.call(model, action, [recordIds], {context: context});
        if (res) {
            await this.actionService.doAction(res, {
                additionalContext: {
                    dont_redirect_to_payments: 1,
                },
                onClose: async () => {
                    await this.model.root.load();
                    this.render(true);
                }
            });
        }
        await this.model.root.load();
    }
}

export class ExpenseListRenderer extends ExpenseDocumentDropZone(ExpenseMobileQRCode(ListRenderer)) {}
ExpenseListRenderer.template = 'hr_expense.ListRenderer';

export class ExpenseDashboardListRenderer extends ExpenseListRenderer {}

ExpenseDashboardListRenderer.components = { ...ExpenseDashboardListRenderer.components, ExpenseDashboard};
ExpenseDashboardListRenderer.template = 'hr_expense.DashboardListRenderer';

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
