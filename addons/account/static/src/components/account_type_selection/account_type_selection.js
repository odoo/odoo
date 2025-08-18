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
        this.sections = [
            {
                label: _t('Balance Sheet'),
                name: "balance_sheet"
            },
            {
                label: _t('Profit & Loss'),
                name: "profit_and_loss"
            },
        ]
        this.groups = [
            {
                label: _t('Assets'),
                choices: getChoicesForGroup('asset'),
                section: "balance_sheet",
            },
            {
                label: _t('Liabilities'),
                choices: getChoicesForGroup('liability'),
                section: "balance_sheet",
            },
            {
                label: _t('Equity'),
                choices: getChoicesForGroup('equity'),
                section: "balance_sheet",
            },
            {
                label: _t('Income'),
                choices: getChoicesForGroup('income'),
                section: "profit_and_loss",
            },
            {
                label: _t('Expense'),
                choices: getChoicesForGroup('expense'),
                section: "profit_and_loss",
            },
            {
                label: _t('Other'),
                choices: getChoicesForGroup('off_balance'),
                section: "profit_and_loss",
            },
        ];
    }
}

export const accountTypeSelection = {
    ...selectionField,
    component: AccountTypeSelection,
};

registry.category("fields").add("account_type_selection", accountTypeSelection);
