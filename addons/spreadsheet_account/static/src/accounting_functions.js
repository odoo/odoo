/** @odoo-module native */
import * as spreadsheet from "@odoo/o-spreadsheet";
import { parsePeriod } from "@spreadsheet/helpers/period";
import { _t } from "@web/core/translation";
const { functionRegistry } = spreadsheet.registries;
const { arg, toBoolean, toString, toNumber, toJsDate } = spreadsheet.helpers;

const YEAR_OFFSET_ARG = arg(
    "offset (number, default=0)",
    _t("Offset applied to the years."),
);
const COMPANY_ARG = arg(
    "company_id (number, optional)",
    _t("The company to target (Advanced)."),
);
const POSTED_ARG = arg(
    "include_unposted (boolean, default=FALSE)",
    _t("Set to TRUE to include unposted entries."),
);

const ODOO_FIN_ARGS = () => [
    arg("account_codes (string)", _t("The prefix of the accounts.")),
    arg(
        "date_range (string, date)",
        _t(
            `The date range. Supported formats are "21/12/2022", "Q1/2022", "12/2022", and "2022".`,
        ),
    ),
    YEAR_OFFSET_ARG,
    COMPANY_ARG,
    POSTED_ARG,
];

const ODOO_RESIDUAL_ARGS = () => [
    arg(
        "account_codes (string, optional)",
        _t(
            "The prefix of the accounts. If none provided, all receivable and payable accounts will be used.",
        ),
    ),
    arg(
        "date_range (string, date, optional)",
        _t(
            `The date range. Supported formats are "21/12/2022", "Q1/2022", "12/2022", and "2022".`,
        ),
    ),
    YEAR_OFFSET_ARG,
    COMPANY_ARG,
    POSTED_ARG,
];

const ODOO_PARTNER_BALANCE_ARGS = () => {
    const partner_arg = arg(
        "partner_ids (string)",
        _t("The partner ids (separated by a comma)."),
    );
    return [partner_arg, ...ODOO_RESIDUAL_ARGS()];
};

functionRegistry.add("ODOO.CREDIT", {
    description: _t("Get the total credit for the specified account(s) and period."),
    args: ODOO_FIN_ARGS(),
    category: "Odoo",
    returns: ["NUMBER"],
    compute: function (
        accountCodes,
        dateRange,
        offset = { value: 0 },
        companyId = { value: null },
        includeUnposted = { value: false },
    ) {
        const _accountCodes = toString(accountCodes)
            .split(",")
            .map((code) => code.trim())
            .sort();
        const _offset = toNumber(offset, this.locale);
        const _dateRange = parsePeriod(dateRange, this.locale);
        const _companyId = companyId?.value;
        const _includeUnposted = toBoolean(includeUnposted);
        return {
            value: this.getters.getAccountPrefixCredit(
                _accountCodes,
                _dateRange,
                _offset,
                _companyId,
                _includeUnposted,
            ),
            format: this.getters.getCompanyCurrencyFormat(_companyId) || "#,##0.00",
        };
    },
});

functionRegistry.add("ODOO.DEBIT", {
    description: _t("Get the total debit for the specified account(s) and period."),
    args: ODOO_FIN_ARGS(),
    category: "Odoo",
    returns: ["NUMBER"],
    compute: function (
        accountCodes,
        dateRange,
        offset = { value: 0 },
        companyId = { value: null },
        includeUnposted = { value: false },
    ) {
        const _accountCodes = toString(accountCodes)
            .split(",")
            .map((code) => code.trim())
            .sort();
        const _offset = toNumber(offset, this.locale);
        const _dateRange = parsePeriod(dateRange, this.locale);
        const _companyId = companyId?.value;
        const _includeUnposted = toBoolean(includeUnposted);
        return {
            value: this.getters.getAccountPrefixDebit(
                _accountCodes,
                _dateRange,
                _offset,
                _companyId,
                _includeUnposted,
            ),
            format: this.getters.getCompanyCurrencyFormat(_companyId) || "#,##0.00",
        };
    },
});

functionRegistry.add("ODOO.BALANCE", {
    description: _t("Get the total balance for the specified account(s) and period."),
    args: ODOO_FIN_ARGS(),
    category: "Odoo",
    returns: ["NUMBER"],
    compute: function (
        accountCodes,
        dateRange,
        offset = { value: 0 },
        companyId = { value: null },
        includeUnposted = { value: false },
    ) {
        const _accountCodes = toString(accountCodes)
            .split(",")
            .map((code) => code.trim())
            .sort();
        const _offset = toNumber(offset, this.locale);
        const _dateRange = parsePeriod(dateRange, this.locale);
        const _companyId = companyId?.value;
        const _includeUnposted = toBoolean(includeUnposted);
        const value =
            this.getters.getAccountPrefixDebit(
                _accountCodes,
                _dateRange,
                _offset,
                _companyId,
                _includeUnposted,
            ) -
            this.getters.getAccountPrefixCredit(
                _accountCodes,
                _dateRange,
                _offset,
                _companyId,
                _includeUnposted,
            );
        return {
            value,
            format: this.getters.getCompanyCurrencyFormat(_companyId) || "#,##0.00",
        };
    },
});

functionRegistry.add("ODOO.FISCALYEAR.START", {
    description: _t(
        "Returns the starting date of the fiscal year encompassing the provided date.",
    ),
    args: [
        arg("day (date)", _t("The day from which to extract the fiscal year start.")),
        arg("company_id (number, optional)", _t("The company.")),
    ],
    category: "Odoo",
    returns: ["NUMBER"],
    compute: function (date, companyId = { value: null }) {
        const startDate = this.getters.getFiscalStartDate(
            toJsDate(date, this.locale),
            companyId.value === null ? null : toNumber(companyId, this.locale),
        );
        return {
            value: toNumber(startDate, this.locale),
            format: this.locale.dateFormat,
        };
    },
});

functionRegistry.add("ODOO.FISCALYEAR.END", {
    description: _t(
        "Returns the ending date of the fiscal year encompassing the provided date.",
    ),
    args: [
        arg("day (date)", _t("The day from which to extract the fiscal year end.")),
        arg("company_id (number, optional)", _t("The company.")),
    ],
    category: "Odoo",
    returns: ["NUMBER"],
    compute: function (date, companyId = { value: null }) {
        const endDate = this.getters.getFiscalEndDate(
            toJsDate(date, this.locale),
            companyId.value === null ? null : toNumber(companyId, this.locale),
        );
        return {
            value: toNumber(endDate, this.locale),
            format: this.locale.dateFormat,
        };
    },
});

const ACCOUNT_TYPES = [
    "asset_receivable",
    "asset_cash",
    "asset_current",
    "asset_non_current",
    "asset_prepayments",
    "asset_fixed",
    "liability_payable",
    "liability_credit_card",
    "liability_current",
    "liability_non_current",
    "equity",
    "equity_unaffected",
    "income",
    "income_other",
    "expense",
    "expense_depreciation",
    "expense_direct_cost",
    "off_balance",
];

functionRegistry.add("ODOO.ACCOUNT.GROUP", {
    description: _t("Returns the account codes of a given group."),
    args: [
        arg(
            "type (string)",
            _t(
                "The technical account type (possible values are: %s).",
                ACCOUNT_TYPES.join(", "),
            ),
        ),
    ],
    category: "Odoo",
    returns: ["NUMBER"],
    compute: function (accountType) {
        const accountTypes = this.getters.getAccountGroupCodes(toString(accountType));
        return accountTypes.join(",");
    },
});

functionRegistry.add("ODOO.RESIDUAL", {
    description: _t(
        "Return the residual amount for the specified account(s) and period",
    ),
    args: ODOO_RESIDUAL_ARGS(),
    category: "Odoo",
    returns: ["NUMBER"],
    compute: function (
        accountCodes,
        dateRange,
        offset = { value: 0 },
        companyId = { value: null },
        includeUnposted = { value: false },
    ) {
        const _accountCodes = toString(accountCodes)
            .split(",")
            .map((code) => code.trim())
            .sort();
        const _offset = toNumber(offset, this.locale);
        if (!dateRange?.value) {
            dateRange = { value: new Date().getFullYear() };
        }
        const _dateRange = parsePeriod(dateRange, this.locale);
        const _companyId = toNumber(companyId, this.locale);
        const _includeUnposted = toBoolean(includeUnposted);
        return {
            value: this.getters.getAccountResidual(
                _accountCodes,
                _dateRange,
                _offset,
                _companyId,
                _includeUnposted,
            ),
            format: this.getters.getCompanyCurrencyFormat(_companyId) || "#,##0.00",
        };
    },
});

functionRegistry.add("ODOO.PARTNER.BALANCE", {
    description: _t(
        "Return the partner balance for the specified account(s) and period",
    ),
    args: ODOO_PARTNER_BALANCE_ARGS(),
    category: "Odoo",
    returns: ["NUMBER"],
    compute: function (
        partnerIds,
        accountCodes,
        dateRange,
        offset = { value: 0 },
        companyId = { value: null },
        includeUnposted = { value: false },
    ) {
        const _partnerIds = toString(partnerIds)
            .split(",")
            .map((partnerId) => toNumber(partnerId, this.locale))
            .sort();
        const _accountCodes = toString(accountCodes)
            .split(",")
            .map((code) => code.trim())
            .sort();
        const _offset = toNumber(offset, this.locale);

        if (!dateRange?.value) {
            dateRange = { value: new Date().getFullYear() };
        }
        const _dateRange = parsePeriod(dateRange, this.locale);
        const _companyId = toNumber(companyId, this.locale);
        const _includeUnposted = toBoolean(includeUnposted);
        return {
            value: this.getters.getAccountPartnerData(
                _accountCodes,
                _dateRange,
                _offset,
                _companyId,
                _includeUnposted,
                _partnerIds,
            ),
            format: this.getters.getCompanyCurrencyFormat(_companyId) || "#,##0.00",
        };
    },
});

functionRegistry.add("ODOO.BALANCE.TAG", {
    description: _t(
        "Return the balance of accounts for the specified tag(s) and period",
    ),
    args: [
        arg("account_tag_ids (string)", _t("The tag ids (separated by a comma).")),
        arg(
            "date_range (string, date, optional)",
            _t(
                `The date range. Supported formats are "21/12/2022", "Q1/2022", "12/2022", and "2022".`,
            ),
        ),
        YEAR_OFFSET_ARG,
        COMPANY_ARG,
        POSTED_ARG,
    ],
    category: "Odoo",
    returns: ["NUMBER"],
    compute: function (
        accountTagIds,
        dateRange,
        offset = { value: 0 },
        companyId = { value: null },
        includeUnposted = { value: false },
    ) {
        const _accountTagIds = toString(accountTagIds)
            .split(",")
            .map((accountTagId) => toNumber(accountTagId, this.locale))
            .sort();
        const _offset = toNumber(offset, this.locale);

        if (!dateRange?.value) {
            dateRange = { value: new Date().getFullYear() };
        }
        const _dateRange = parsePeriod(dateRange, this.locale);
        const _companyId = toNumber(companyId, this.locale);
        const _includeUnposted = toBoolean(includeUnposted);
        return {
            value: this.getters.getAccountTagData(
                _accountTagIds,
                _dateRange,
                _offset,
                _companyId,
                _includeUnposted,
            ),
            format: this.getters.getCompanyCurrencyFormat(_companyId) || "#,##0.00",
        };
    },
});
