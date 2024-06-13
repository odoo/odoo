/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { SelectionField, selectionField } from "@web/views/fields/selection/selection_field";

export class AccountTypeSelection extends SelectionField {
    static template = "account.AccountTypeSelection";
    get hierarchyOptions() {
        const opts = this.options;
        return [
            { name: _t('Balance Sheet') },
            { name: _t('Assets'), children: opts.filter(x => x[0] && x[0].startsWith('asset')) },
            { name: _t('Liabilities'), children: opts.filter(x => x[0] && x[0].startsWith('liability')) },
            { name: _t('Equity'), children: opts.filter(x => x[0] && x[0].startsWith('equity')) },
            { name: _t('Profit & Loss') },
            { name: _t('Income'), children: opts.filter(x => x[0] && x[0].startsWith('income')) },
            { name: _t('Expense'), children: opts.filter(x => x[0] && x[0].startsWith('expense')) },
            { name: _t('Other'), children: opts.filter(x => x[0] && x[0] === 'off_balance') },
        ];
    }
}

export const accountTypeSelection = {
    ...selectionField,
    component: AccountTypeSelection,
};

registry.category("fields").add("account_type_selection", accountTypeSelection);
