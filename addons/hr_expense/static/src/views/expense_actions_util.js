import { user } from "@web/core/user";

import { _t } from "@web/core/l10n/translation";

export class ExpenseActionsUtil {
    constructor(controller) {
        this.controller = controller;
    }

    async onWillStartUtil() {
        // note for JUAL: maybe this can bring confusion, and we could just let the following code in
        // controllers (Kanban and List), and no onWillStart in here ?
        // It would be a bit repetitive, but would make the code cleaner and easier to read IMO...
        /*
        * setup() {
        *   ...
        *   onWillStart(async () => {
        *       this.userIsExpenseTeamApprover = await user.hasGroup("hr_expense.group_hr_expense_team_approver");
        *       this.userIsAccountInvoicing = await user.hasGroup("account.group_account_invoice");
        *   )};
        * }
        * */

        // 'this' references the controller (see how it's called in ExpenseListController)
        this.userIsExpenseTeamApprover = await user.hasGroup("hr_expense.group_hr_expense_team_approver");
        this.userIsAccountInvoicing = await user.hasGroup("account.group_account_invoice");
    }

    display(action) {
        const records = this.controller.model.root.selection;
        const action_map = {
            'action_submit': {'role': true, 'state': 'draft'},
            'action_approve': {'role': this.controller.userIsExpenseTeamApprover, 'state': 'submitted'},
            'action_post': {'role': this.controller.userIsAccountInvoicing, 'state': 'approved'},
        }
        const action_data = action_map[action];
        return records.length && action_data?.role && records.every(record => record.data.state === action_data?.state);
    }

    async onClick(action) {
        const records = this.controller.model.root.selection;
        const recordIds = records.map((a) => a.resId);
        const model = this.controller.model.config.resModel;
        const context = {};
        if (action === 'action_approve') {
            context['validate_analytic'] = true;
        }
        const res = await this.controller.orm.call(model, action, [recordIds], {context: context});
        if (res) {
            await this.controller.actionService.doAction(res, {
                additionalContext: {
                    dont_redirect_to_payments: 1,
                },
                onClose: async (closeParams) => {
                    if (closeParams?.noReload) {
                        return;
                    }
                    await this.controller.model.root.load();
                    this.controller.render(true);
                }
            });
        }
        await this.controller.model.root.load();
    }

    getExtraStaticActionMenuItems() {
        return {
            "submitExpense": this.getMenuItem('action_submit', "Submit", 997),
            "approveExpense": this.getMenuItem('action_approve', "Approve", 998),
            "postExpense": this.getMenuItem('action_post', "Post Entries", 999),
        }
    }

    getMenuItem(action, title, seq) {
        return {
            isAvailable: () => this.controller.props.resModel === 'hr.expense' && this.controller.env.isSmall && this.display(action),
            sequence: seq,
            description: _t(title),
            callback: () => this.onClick(action),
        }
    }
}
