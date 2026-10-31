import { user } from "@web/core/user";
import { onWillStart } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";

import { ExpenseDocumentUpload } from './document_upload';

export const ExpenseCollectionAction = (T) => class ExpenseCollectionAction extends ExpenseDocumentUpload(T) {
    setup() {
        super.setup();

        onWillStart(async () => {
            this.userIsExpenseTeamApprover = await user.hasGroup("hr_expense.group_hr_expense_team_approver");
            this.userIsAccountInvoicing = await user.hasGroup("account.group_account_invoice");
        });
    }

    _displayAction(action) {
        const records = this.model.root.selection;
        const action_map = {
            'action_submit': {'role': true, 'state': 'draft'},
            'action_approve': {'role': this.userIsExpenseTeamApprover, 'state': 'submitted'},
            'action_post': {'role': this.userIsAccountInvoicing, 'state': 'approved'},
        };
        const action_data = action_map[action];
        return records.length && action_data?.role && records.every(record => record.data.state === action_data?.state);
    }

    async onClick(action) {
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
            "submitExpense": this._getMenuItem('action_submit', "Submit", 997),
            "approveExpense": this._getMenuItem('action_approve', "Approve", 998),
            "postExpense": this._getMenuItem('action_post', "Post Entries", 999),
        };
    }

    _getMenuItem(action, title, seq) {
        return {
            isAvailable: () => this.props.resModel === 'hr.expense' && this.env.isSmall && this._displayAction(action),
            sequence: seq,
            description: _t(title),
            callback: () => this.onClick(action),
        };
    }
};
