import { render } from "@web/owl2/utils";
import { ExpenseDashboard } from "@hr_expense/components/expense_dashboard";
import { ExpenseDocumentUpload, ExpenseDocumentDropZone } from "@hr_expense/mixins/document_upload";

import { registry } from '@web/core/registry';
import { useService } from '@web/core/utils/hooks';
import { user } from "@web/core/user";
import { rpc } from "@web/core/network/rpc";
import { listView } from "@web/views/list/list_view";

import { ListController } from "@web/views/list/list_controller";
import { ListRenderer, listRendererProps } from "@web/views/list/list_renderer";
import { onWillStart } from "@odoo/owl";

export class ExpenseListController extends ExpenseDocumentUpload(ListController) {
    static template = `hr_expense.ListView`;

    setup() {
        super.setup();
        this.orm = useService('orm');
        this.actionService = useService('action');

        onWillStart(async () => {
            [this.userIsExpenseTeamApprover, this.userIsAccountInvoicing, this.userHasEmployee] =
                await Promise.all([
                    user.hasGroup("hr_expense.group_hr_expense_team_approver"),
                    user.hasGroup("account.group_account_invoice"),
                    rpc(
                        "/web/dataset/call_kw/res.users/read",
                        {
                            model: "res.users",
                            method: "read",
                            args: [[user.userId], ["employee_id"]],
                            kwargs: { context: user.context },
                        },
                        { cache: { type: "disk" } }
                    ).then((r) => !!r?.[0]?.employee_id),
                ]);
            if (!this.userHasEmployee && !this.userIsExpenseTeamApprover) {
                this.activeActions.create = false;
            }
        });
    }

    displaySubmit() {
        const records = this.model.root.selection;
        return records.length && records.every(record => record.data.state === 'draft');
    }

    displayApprove() {
        const records = this.model.root.selection;
        return this.userIsExpenseTeamApprover && records.length && records.every(record => record.data.state === 'submitted');
    }

    displayPost() {
        const records = this.model.root.selection;
        return this.userIsAccountInvoicing && records.length && records.every(record => record.data.state === 'approved');
    }

    async onClick (action) {
        const records = this.model.root.selection;
        const recordIds = records.map((a) => a.resId);
        const model = this.model.config.resModel;
        const context = {};
        if (action === 'action_approve') {
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
                    render(this, true);
                }
            });
        }
        await this.model.root.load();
    }
}

export class ExpenseListRenderer extends ExpenseDocumentDropZone(ListRenderer, listRendererProps) {
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
