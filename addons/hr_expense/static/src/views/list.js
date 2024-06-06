/** @odoo-module */

import { ExpenseDashboard } from '../components/expense_dashboard';
import { ExpenseMobileQRCode } from '../mixins/qrcode';
import { ExpenseDocumentUpload, ExpenseDocumentDropZone } from '../mixins/document_upload';

import { registry } from '@web/core/registry';
import { patch } from '@web/core/utils/patch';
import { useService } from '@web/core/utils/hooks';
import { listView } from "@web/views/list/list_view";

import { ListController } from "@web/views/list/list_controller";
import { ListRenderer } from "@web/views/list/list_renderer";

const { onWillStart } = owl;

export class ExpenseListController extends ListController {
    setup() {
        super.setup();
        this.orm = useService('orm');
        this.actionService = useService('action');
        this.rpc = useService("rpc");
        this.user = useService("user");
        this.isExpenseSheet = this.model.rootParams.resModel === "hr.expense.sheet";
        this.isExpense = this.model.rootParams.resModel === "hr.expense";

        onWillStart(async () => {
            this.is_expense_team_approver = await this.user.hasGroup("hr_expense.group_hr_expense_team_approver");
            this.is_account_invoicing = await this.user.hasGroup("account.group_account_invoice");
        });
    }

    displayCreateReport() {
        return this.isExpense;
    }

    displaySubmit() {
        const records = this.model.root.selection;
        return records.length && records.every(record => record.data.state === 'draft') && this.isExpenseSheet;
    }

    displayApprove() {
        const records = this.model.root.selection;
        return this.is_expense_team_approver && records.length && records.every(record => record.data.state === 'submit') && this.isExpenseSheet;
    }

    displayPost() {
        const records = this.model.root.selection;
        return this.is_account_invoicing && records.length && records.every(record => record.data.state === 'approve') && this.isExpenseSheet;
    }

    async onClick (action) {
        const records = this.model.root.selection;
        const recordIds = records.map((a) => a.resId);
        const model = this.model.rootParams.resModel;
        const context = {};
        if (action === 'approve_expense_sheets') {
            context['validate_analytic'] = true;
        }
        await this.orm.call(model, action, [recordIds], {context: context});
        // sgv note: we tried this.model.notify(); and does not work
        await this.model.root.load();
        this.render(true);
    }

    async onCreateReportClick() {
        const records = this.model.root.selection;
        const recordIds = records.map((a) => a.resId);
        const action = await this.orm.call('hr.expense', 'get_expenses_to_submit', [recordIds]);
        this.actionService.doAction(action);
    }

}
patch(ExpenseListController.prototype, 'expense_list_controller_upload', ExpenseDocumentUpload);

export class ExpenseListRenderer extends ListRenderer {
    setup() {
        super.setup()
    }
}
patch(ExpenseListRenderer.prototype, 'expense_list_renderer_qrcode', ExpenseMobileQRCode);
patch(ExpenseListRenderer.prototype, 'expense_list_renderer_qrcode_dzone', ExpenseDocumentDropZone);
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
