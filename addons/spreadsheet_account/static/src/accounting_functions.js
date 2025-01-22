/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { sprintf } from "@web/core/utils/strings";

import * as spreadsheet from "@odoo/o-spreadsheet";
import { EvaluationError } from "@odoo/o-spreadsheet";
const { functionRegistry } = spreadsheet.registries;
const { arg, toBoolean, toString, toNumber, toJsDate } = spreadsheet.helpers;

const QuarterRegexp = /^q([1-4])\/(\d{4})$/i;
const MonthRegexp = /^0?([1-9]|1[0-2])\/(\d{4})$/i;

/**
 * @typedef {Object} YearDateRange
 * @property {"year"} rangeType
 * @property {number} year
 */

/**
 * @typedef {Object} QuarterDateRange
 * @property {"quarter"} rangeType
 * @property {number} year
 * @property {number} quarter
 */

/**
 * @typedef {Object} MonthDateRange
 * @property {"month"} rangeType
 * @property {number} year
 * @property {number} month
 */

/**
 * @typedef {Object} DayDateRange
 * @property {"day"} rangeType
 * @property {number} year
 * @property {number} month
 * @property {number} day
 */

/**
 * @typedef {YearDateRange | QuarterDateRange | MonthDateRange | DayDateRange} DateRange
 */

/**
 * @param {object | undefined} dateRange
 * @returns {QuarterDateRange | undefined}
 */
function parseAccountingQuarter(dateRange) {
    const found = toString(dateRange?.value).trim().match(QuarterRegexp);
    return found
        ? {
              rangeType: "quarter",
              year: Number(found[2]),
              quarter: Number(found[1]),
          }
        : undefined;
}

/**
 * @param {object | undefined} dateRange
 * @returns {MonthDateRange | undefined}
 */
function parseAccountingMonth(dateRange, locale) {
    if (
        typeof dateRange?.value === "number" &&
        dateRange.format?.includes("m") &&
        !dateRange.format?.includes("d")
    ) {
        const date = toJsDate(dateRange.value, locale);
        return {
            rangeType: "month",
            year: date.getFullYear(),
            month: date.getMonth() + 1,
        };
    }
    const found = toString(dateRange?.value).trim().match(MonthRegexp);
    return found
        ? {
              rangeType: "month",
              year: Number(found[2]),
              month: Number(found[1]),
          }
        : undefined;
}

/**
 * @param {object | undefined} dateRange
 * @returns {YearDateRange | undefined}
 */
function parseAccountingYear(dateRange, locale) {
    const dateNumber = toNumber(dateRange?.value, locale);
    // This allows a bit of flexibility for the user if they were to input a
    // numeric value instead of a year.
    // Users won't need to fetch accounting info for year 3000 before a long time
    // And the numeric value 3000 corresponds to 18th march 1908, so it's not an
    //issue to prevent them from fetching accounting data prior to that date.
    if (dateNumber < 3000) {
        return { rangeType: "year", year: dateNumber };
    }
    return undefined;
}

/**
 * @param {object | undefined} dateRange
 * @returns {DayDateRange}
 */
function parseAccountingDay(dateRange, locale) {
    const dateNumber = toNumber(dateRange?.value, locale);
    return {
        rangeType: "day",
        year: functionRegistry.get("YEAR").compute.bind({ locale })(dateNumber),
        month: functionRegistry.get("MONTH").compute.bind({ locale })(dateNumber),
        day: functionRegistry.get("DAY").compute.bind({ locale })(dateNumber),
    };
}

/**
 * @param {object | undefined} dateRange
 * @returns {DateRange}
 */
export function parseAccountingDate(dateRange, locale) {
    try {
        return (
            parseAccountingQuarter(dateRange) ||
            parseAccountingMonth(dateRange, locale) ||
            parseAccountingYear(dateRange, locale) ||
            parseAccountingDay(dateRange, locale)
        );
    } catch {
        throw new EvaluationError(
            sprintf(
                _t(
                    `'%s' is not a valid period. Supported formats are "21/12/2022", "Q1/2022", "12/2022", and "2022".`
                ),
                dateRange?.value
            )
        );
    }
}

const YEAR_OFFSET_ARG = arg("offset (number, default=0)", _t("Offset applied to the years."))
const COMPANY_ARG = arg("company_id (number, optional)", _t("The company to target (Advanced)."))
const POSTED_ARG = arg(
    "include_unposted (boolean, default=FALSE)",
    _t("Set to TRUE to include unposted entries.")
)

const ODOO_FIN_ARGS = () => [
    arg("account_codes (string)", _t("The prefix of the accounts.")),
    arg(
        "date_range (string, date)",
        _t(`The date range. Supported formats are "21/12/2022", "Q1/2022", "12/2022", and "2022".`)
    ),
    YEAR_OFFSET_ARG,
    COMPANY_ARG,
    POSTED_ARG,
];

const ODOO_RESIDUAL_ARGS = () => [
    arg(
        "account_codes (string, optional)",
        _t("The prefix of the accounts. If none provided, all receivable and payable accounts will be used.")
    ),
    arg(
        "date_range (string, date, optional)",
        _t(`The date range. Supported formats are "21/12/2022", "Q1/2022", "12/2022", and "2022".`)
    ),
    YEAR_OFFSET_ARG,
    COMPANY_ARG,
    POSTED_ARG,
];

const ODOO_PARTNER_BALANCE_ARGS = () => {
    const partner_arg = arg("partner_ids (string)", _t("The partner ids (separated by a comma)."));
    return [partner_arg, ...ODOO_RESIDUAL_ARGS()];
}

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
        includeUnposted = { value: false }
    ) {
        const _accountCodes = toString(accountCodes)
            .split(",")
            .map((code) => code.trim())
            .sort();
        const _offset = toNumber(offset, this.locale);
        const _dateRange = parseAccountingDate(dateRange, this.locale);
        const _companyId = companyId?.value;
        const _includeUnposted = toBoolean(includeUnposted);
        return {
            value: this.getters.getAccountPrefixCredit(
                _accountCodes,
                _dateRange,
                _offset,
                _companyId,
                _includeUnposted
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
        includeUnposted = { value: false }
    ) {
        const _accountCodes = toString(accountCodes)
            .split(",")
            .map((code) => code.trim())
            .sort();
        const _offset = toNumber(offset, this.locale);
        const _dateRange = parseAccountingDate(dateRange, this.locale);
        const _companyId = companyId?.value;
        const _includeUnposted = toBoolean(includeUnposted);
        return {
            value: this.getters.getAccountPrefixDebit(
                _accountCodes,
                _dateRange,
                _offset,
                _companyId,
                _includeUnposted
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
        includeUnposted = { value: false }
    ) {
        const _accountCodes = toString(accountCodes)
            .split(",")
            .map((code) => code.trim())
            .sort();
        const _offset = toNumber(offset, this.locale);
        const _dateRange = parseAccountingDate(dateRange, this.locale);
        const _companyId = companyId?.value;
        const _includeUnposted = toBoolean(includeUnposted);
        const value =
            this.getters.getAccountPrefixDebit(
                _accountCodes,
                _dateRange,
                _offset,
                _companyId,
                _includeUnposted
            ) -
            this.getters.getAccountPrefixCredit(
                _accountCodes,
                _dateRange,
                _offset,
                _companyId,
                _includeUnposted
            );
        return { value, format: this.getters.getCompanyCurrencyFormat(_companyId) || "#,##0.00" };
    },
});

functionRegistry.add("ODOO.FISCALYEAR.START", {
    description: _t("Returns the starting date of the fiscal year encompassing the provided date."),
    args: [
        arg("day (date)", _t("The day from which to extract the fiscal year start.")),
        arg("company_id (number, optional)", _t("The company.")),
    ],
    category: "Odoo",
    returns: ["NUMBER"],
    compute: function (date, companyId = { value: null }) {
        const startDate = this.getters.getFiscalStartDate(
            toJsDate(date, this.locale),
            companyId.value === null ? null : toNumber(companyId, this.locale)
        );
        return {
            value: toNumber(startDate, this.locale),
            format: this.locale.dateFormat,
        };
    },
});

functionRegistry.add("ODOO.FISCALYEAR.END", {
    description: _t("Returns the ending date of the fiscal year encompassing the provided date."),
    args: [
        arg("day (date)", _t("The day from which to extract the fiscal year end.")),
        arg("company_id (number, optional)", _t("The company.")),
    ],
    category: "Odoo",
    returns: ["NUMBER"],
    compute: function (date, companyId = { value: null }) {
        const endDate = this.getters.getFiscalEndDate(
            toJsDate(date, this.locale),
            companyId.value === null ? null : toNumber(companyId, this.locale)
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
            _t("The technical account type (possible values are: %s).", ACCOUNT_TYPES.join(", "))
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
    description: _t("Return the residual amount for the specified account(s) and period"),
    args: ODOO_RESIDUAL_ARGS(),
    category: "Odoo",
    returns: ["NUMBER"],
    compute: function (
        accountCodes,
        dateRange,
        offset = { value: 0 },
        companyId = { value: null },
        includeUnposted = { value: false }
    ) {
        const _accountCodes = toString(accountCodes)
            .split(",")
            .map((code) => code.trim())
            .sort();
        const _offset = toNumber(offset, this.locale);
        if ( !dateRange?.value ) {
            dateRange = { value: new Date().getFullYear() }
        }
        const _dateRange = parseAccountingDate(dateRange, this.locale);
        const _companyId = toNumber(companyId, this.locale);
        const _includeUnposted = toBoolean(includeUnposted);
        return {
            value: this.getters.getAccountResidual(
                _accountCodes,
                _dateRange,
                _offset,
                _companyId,
                _includeUnposted
            ),
            format: this.getters.getCompanyCurrencyFormat(_companyId) || "#,##0.00",
        };
    },
})

functionRegistry.add("ODOO.PARTNER.BALANCE", {
    description: _t("Return the partner balance for the specified account(s) and period"),
    args: ODOO_PARTNER_BALANCE_ARGS(),
    category: "Odoo",
    returns: ["NUMBER"],
    compute: function (
        partnerIds,
        accountCodes,
        dateRange,
        offset = { value: 0 },
        companyId = { value: null },
        includeUnposted = { value: false }
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

        if ( !dateRange?.value ) {
            dateRange = { value: new Date().getFullYear() }
        }
        const _dateRange = parseAccountingDate(dateRange, this.locale);
        const _companyId = toNumber(companyId, this.locale);
        const _includeUnposted = toBoolean(includeUnposted);
        return {
            value: this.getters.getAccountPartnerData(
                _accountCodes,
                _dateRange,
                _offset,
                _companyId,
                _includeUnposted,
                _partnerIds
            ),
            format: this.getters.getCompanyCurrencyFormat(_companyId) || "#,##0.00",
        };
    },
})
