/** @odoo-module **/

import { registry } from "@web/core/registry";
import { SelectionField } from "@web/views/fields/selection/selection_field";

export class AccountTypeSelection extends SelectionField {
    get hierarchyOptions() {
        const opts = this.options;
        return [
            { name: this.env._t('Balance Sheet') },
            { name: this.env._t('Assets'), children: opts.filter(x => x[0] && x[0].startsWith('asset')) },
            { name: this.env._t('Liabilities'), children: opts.filter(x => x[0] && x[0].startsWith('liability')) },
            { name: this.env._t('Equity'), children: opts.filter(x => x[0] && x[0].startsWith('equity')) },
            { name: this.env._t('Profit & Loss') },
            { name: this.env._t('Income'), children: opts.filter(x => x[0] && x[0].startsWith('income')) },
            { name: this.env._t('Expense'), children: opts.filter(x => x[0] && x[0].startsWith('expense')) },
            { name: this.env._t('Other'), children: opts.filter(x => x[0] && x[0] === 'off_balance') },
        ];
    }
}
AccountTypeSelection.template = "account.AccountTypeSelection";

registry.category("fields").add("account_type_selection", AccountTypeSelection);
