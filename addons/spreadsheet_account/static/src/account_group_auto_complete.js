import { _t } from "@web/core/l10n/translation";

import { registries, tokenColors, helpers } from "@odoo/o-spreadsheet";

const { insertTokenAfterLeftParenthesis } = helpers;

// copy-pasted list of options from the `account_type` selection field.
const ACCOUNT_TYPES = [
    ["asset_receivable", _t("Receivable")],
    ["asset_cash", _t("Bank and Cash")],
    ["asset_current", _t("Current Assets")],
    ["asset_non_current", _t("Non-current Assets")],
    ["asset_prepayments", _t("Prepayments")],
    ["asset_fixed", _t("Fixed Assets")],
    ["liability_payable", _t("Payable")],
    ["liability_credit_card", _t("Credit Card")],
    ["liability_current", _t("Current Liabilities")],
    ["liability_non_current", _t("Non-current Liabilities")],
    ["equity", _t("Equity")],
    ["equity_unaffected", _t("Current Year Earnings")],
    ["income", _t("Income")],
    ["income_other", _t("Other Income")],
    ["expense", _t("Expenses")],
    ["expense_depreciation", _t("Depreciation")],
    ["expense_direct_cost", _t("Cost of Revenue")],
    ["off_balance", _t("Off-Balance Sheet")],
];

registries.autoCompleteProviders.add("account_group_types", {
    sequence: 50,
    autoSelectFirstProposal: true,
    getProposals(tokenAtCursor) {
        const functionContext = tokenAtCursor.functionContext;
        if (
            functionContext?.parent.toUpperCase() === "ODOO.ACCOUNT.GROUP" &&
            functionContext.argPosition === 0
        ) {
            return ACCOUNT_TYPES.map(([technicalName, displayName]) => {
                const text = `"${technicalName}"`;
                return {
                    text,
                    description: displayName,
                    htmlContent: [{ value: text, color: tokenColors.STRING }],
                    fuzzySearchKey: technicalName + displayName,
                };
            });
        }
        return;
    },
    selectProposal: insertTokenAfterLeftParenthesis,
});
