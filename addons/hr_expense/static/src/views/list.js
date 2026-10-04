import { ExpenseDashboard } from '../components/expense_dashboard';
import { ExpenseMobileQRCode } from '../mixins/qrcode';
import { ExpenseDocumentUpload, ExpenseDocumentDropZone } from '../mixins/document_upload';

import { registry } from '@web/core/registry';
import { useService } from '@web/core/utils/hooks';
import { user } from "@web/core/user";
import { listView } from "@web/views/list/list_view";

import { ListController } from "@web/views/list/list_controller";
import { ListRenderer } from "@web/views/list/list_renderer";
import { onWillStart } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";

export class ExpenseListController extends ExpenseDocumentUpload(ListController) {
    static template = `hr_expense.ListView`;

    setup() {
        super.setup();
        this.orm = useService('orm');
        this.actionService = useService('action');

        onWillStart(async () => {
            this.userIsExpenseTeamApprover = await user.hasGroup("hr_expense.group_hr_expense_team_approver");
            this.userIsAccountInvoicing = await user.hasGroup("account.group_account_invoice");
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
    displayRefuse() {
        const records = this.model.root.selection;
        return this.userIsExpenseTeamApprover && records.length && records.every(record => ['submitted', 'approved'].includes(record.data.state));
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
            if (action === 'action_refuse') {
                const tmpContext = JSON.parse(res.context.replaceAll("'", '"'));
                tmpContext['active_ids'] = recordIds;
                res.context = JSON.stringify(tmpContext);
            }
            await this.actionService.doAction(res, {
                additionalContext: {
                    dont_redirect_to_payments: 1,
                },
                onClose: async (closeParams) => {
                    if (closeParams?.noReload) {
                        return;
                    }
                    await this.model.root.load();
                    this.render(true);
                }
            });
        }
        await this.model.root.load();
    }

    getStaticActionMenuItems() {
        const menuItems = super.getStaticActionMenuItems(...arguments);
        return {
            ...menuItems,
            "submitExpense": {
                isAvailable: () => this.props.resModel === 'hr.expense' && this.env.isSmall && this.displaySubmit(),
                sequence: 996,
                description: _t("Submit Expenses JS"),
                callback: () => this.onClick('action_submit'),
            },
            "approveExpense": {
                isAvailable: () => this.props.resModel === 'hr.expense' && this.env.isSmall && this.displayApprove(),
                sequence: 997,
                description: _t("Approve Expenses JS"),
                callback: () => this.onClick('action_approve'),
            },
            "refuseExpense": {
                isAvailable: () => this.props.resModel === 'hr.expense' && this.env.isSmall && this.displayRefuse(),
                sequence: 998,
                description: _t("Refuse Expenses JS"),
                callback: () => this.onClick('action_refuse'),
            },
            "postExpense": {
                isAvailable: () => this.props.resModel === 'hr.expense' && this.env.isSmall && this.displayPost(),
                sequence: 999,
                description: _t("Post Expenses JS"),
                callback: () => this.onClick('action_post'),
            }
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
