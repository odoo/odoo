import { _t } from "@web/core/l10n/translation";

import * as spreadsheet from "@odoo/o-spreadsheet";
import { EvaluationError } from "@odoo/o-spreadsheet";
import { computeFormatFromCurrency } from "@spreadsheet/currency/helpers";

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
        year: functionRegistry.get("YEAR").compute.bind({ locale })(dateNumber).value,
        month: functionRegistry.get("MONTH").compute.bind({ locale })(dateNumber).value,
        day: functionRegistry.get("DAY").compute.bind({ locale })(dateNumber).value,
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
            _t(
                `'%s' is not a valid period. Supported formats are "21/12/2022", "Q1/2022", "12/2022", and "2022".`,
                dateRange?.value
            )
        );
    }
}

/**
 * @param {DateRange} dateRange
 * @param {number} offset
 */
function assertDateRangeIsValid(dateRange) {
    // Excel dates start at 1899-12-30, we should not support date ranges
    // that do not cover dates prior to it.
    // Unfortunately, this check needs to be done right before the server
    // call as a date too low (year <= 1) can raise an error server side.
    if (dateRange < 1900) {
        throw new EvaluationError(_t("%s is not a valid year.", dateRange));
    }
}

const YEAR_OFFSET_ARG = arg("offset (number, default=0)", _t("Offset applied to the years."));
const COMPANY_ARG = arg("company_id (number, optional)", _t("The company to target (Advanced)."));
const POSTED_ARG = arg(
    "include_unposted (boolean, default=FALSE)",
    _t("Set to TRUE to include unposted entries.")
);

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
        _t(
            "The prefix of the accounts. If none provided, all receivable and payable accounts will be used."
        )
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
};

/**
 * @param {object} getters
 * @param {number | null} companyId
 * @returns {string}
 */
function getCurrencyFormatOrThrow(getters, companyId) {
    const currency = getters.getCompanyCurrency(companyId);
    if (currency === false) {
        throw new EvaluationError(_t("Currency not available for this company."));
    }
    return computeFormatFromCurrency(currency) || "#,##0.00";
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
        assertDateRangeIsValid(_dateRange.year + _offset);
        const _companyId = companyId.value === null ? null : toNumber(companyId.value, this.locale);
        const _includeUnposted = toBoolean(includeUnposted);
        return {
            value: this.getters.getAccountPrefixCredit(
                _accountCodes,
                _dateRange,
                _offset,
                _companyId,
                _includeUnposted
            ),
            format: getCurrencyFormatOrThrow(this.getters, _companyId),
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
        assertDateRangeIsValid(_dateRange.year + _offset);
        const _companyId = companyId.value === null ? null : toNumber(companyId.value, this.locale);
        const _includeUnposted = toBoolean(includeUnposted);
        return {
            value: this.getters.getAccountPrefixDebit(
                _accountCodes,
                _dateRange,
                _offset,
                _companyId,
                _includeUnposted
            ),
            format: getCurrencyFormatOrThrow(this.getters, _companyId),
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
        assertDateRangeIsValid(_dateRange.year + _offset);
        const _companyId = companyId.value === null ? null : toNumber(companyId.value, this.locale);
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
        return { value, format: getCurrencyFormatOrThrow(this.getters, _companyId) };
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
        const fiscalDates = this.getters.getFiscalDates(
            toJsDate(date, this.locale),
            companyId.value === null ? null : toNumber(companyId, this.locale)
        );
        if (fiscalDates === false) {
            return new EvaluationError(_t("The company fiscal year could not be found."));
        }
        return {
            value: toNumber(fiscalDates.start, this.locale),
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
        const fiscalDates = this.getters.getFiscalDates(
            toJsDate(date, this.locale),
            companyId.value === null ? null : toNumber(companyId, this.locale)
        );
        if (fiscalDates === false) {
            return new EvaluationError(_t("The company fiscal year could not be found."));
        }
        return {
            value: toNumber(fiscalDates.end, this.locale),
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
        return { value: accountTypes.join(",") };
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
        if (!dateRange?.value) {
            dateRange = { value: new Date().getFullYear() };
        }
        const _dateRange = parseAccountingDate(dateRange, this.locale);
        assertDateRangeIsValid(_dateRange.year + _offset);
        const _companyId = toNumber(companyId, this.locale);
        const _includeUnposted = toBoolean(includeUnposted);
        const _accountResidual = this.getters.getAccountResidual(
            _accountCodes,
            _dateRange,
            _offset,
            _companyId,
            _includeUnposted
        );
        if (_accountResidual === false) {
            return new EvaluationError(
                _t("The residual amount for given accounts could not be computed.")
            );
        }
        return {
            value: _accountResidual.amount_residual,
            format: getCurrencyFormatOrThrow(this.getters, _companyId),
        };
    },
});

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

        if (!dateRange?.value) {
            dateRange = { value: new Date().getFullYear() };
        }
        const _dateRange = parseAccountingDate(dateRange, this.locale);
        assertDateRangeIsValid(_dateRange.year + _offset);
        const _companyId = toNumber(companyId, this.locale);
        const _includeUnposted = toBoolean(includeUnposted);
        const _accountPartnerData = this.getters.getAccountPartnerData(
            _accountCodes,
            _dateRange,
            _offset,
            _companyId,
            _includeUnposted,
            _partnerIds
        );
        if (_accountPartnerData === false) {
            return new EvaluationError(_t("The balance for given partners could not be computed."));
        }
        return {
            value: _accountPartnerData.balance,
            format: getCurrencyFormatOrThrow(this.getters, _companyId),
        };
    },
});

functionRegistry.add("ODOO.BALANCE.TAG", {
    description: _t("Return the balance of accounts for the specified tag(s) and period"),
    args: [
        arg("account_tag_ids (string)", _t("The tag ids (separated by a comma).")),
        arg(
            "date_range (string, date, optional)",
            _t(
                `The date range. Supported formats are "21/12/2022", "Q1/2022", "12/2022", and "2022".`
            )
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
        includeUnposted = { value: false }
    ) {
        const _accountTagIds = toString(accountTagIds)
            .split(",")
            .map((accountTagId) => toNumber(accountTagId, this.locale))
            .sort();
        const _offset = toNumber(offset, this.locale);

        if (!dateRange?.value) {
            dateRange = { value: new Date().getFullYear() };
        }
        const _dateRange = parseAccountingDate(dateRange, this.locale);
        assertDateRangeIsValid(_dateRange.year + _offset);
        const _companyId = toNumber(companyId, this.locale);
        const _includeUnposted = toBoolean(includeUnposted);
        const _accountTagData = this.getters.getAccountTagData(
            _accountTagIds,
            _dateRange,
            _offset,
            _companyId,
            _includeUnposted
        );
        if (_accountTagData === false) {
            return new EvaluationError(
                _t("The balance for given account tag could not be computed.")
            );
        }
        return {
            value: _accountTagData.balance,
            format: getCurrencyFormatOrThrow(this.getters, _companyId),
        };
    },
});
