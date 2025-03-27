import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { SelectionField, selectionField } from "@web/views/fields/selection/selection_field";

export class AccountTypeSelection extends SelectionField {
    static template = "account.AccountTypeSelection";
    setup() {
        super.setup();
        const getChoicesForGroup = (group) => {
            return this.choices.filter(x => x.value.startsWith(group));
        }
        this.groups = [
            {
                label: _t('Balance Sheet'),
            },
            {
                label: _t('Assets'),
                choices: getChoicesForGroup('asset'),
            },
            {
                label: _t('Liabilities'),
                choices: getChoicesForGroup('liability'),
            },
            {
                label: _t('Equity'),
                choices: getChoicesForGroup('equity'),
            },
            {
                label: _t('Profit & Loss'),
            },
            {
                label: _t('Income'),
                choices: getChoicesForGroup('income'),
            },
            {
                label: _t('Expense'),
                choices: getChoicesForGroup('expense'),
            },
            {
                label: _t('Other'),
                choices: getChoicesForGroup('off_balance'),
            },
        ];
    }
}

export const accountTypeSelection = {
    ...selectionField,
    component: AccountTypeSelection,
};

registry.category("fields").add("account_type_selection", accountTypeSelection);
