/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { sprintf } from "@web/core/utils/strings";

import * as spreadsheet from "@odoo/o-spreadsheet";
const { functionRegistry } = spreadsheet.registries;
const { arg, toBoolean, toString, toNumber, toJsDate, formatValue } = spreadsheet.helpers;

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
 * @param {string} dateRange
 * @returns {QuarterDateRange | undefined}
 */
function parseAccountingQuarter(dateRange) {
    const found = dateRange.match(QuarterRegexp);
    return found
        ? {
              rangeType: "quarter",
              year: Number(found[2]),
              quarter: Number(found[1]),
          }
        : undefined;
}

/**
 * @param {string} dateRange
 * @returns {MonthDateRange | undefined}
 */
function parseAccountingMonth(dateRange) {
    const found = dateRange.match(MonthRegexp);
    return found
        ? {
              rangeType: "month",
              year: Number(found[2]),
              month: Number(found[1]),
          }
        : undefined;
}

/**
 * @param {string} dateRange
 * @returns {YearDateRange | undefined}
 */
function parseAccountingYear(dateRange, locale) {
    const dateNumber = toNumber(dateRange, locale);
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
 * @param {string} dateRange
 * @returns {DayDateRange}
 */
function parseAccountingDay(dateRange, locale) {
    const dateNumber = toNumber(dateRange, locale);
    return {
        rangeType: "day",
        year: functionRegistry.get("YEAR").compute.bind({ locale })(dateNumber),
        month: functionRegistry.get("MONTH").compute.bind({ locale })(dateNumber),
        day: functionRegistry.get("DAY").compute.bind({ locale })(dateNumber),
    };
}

/**
 * @param {string | number} dateRange
 * @returns {DateRange}
 */
export function parseAccountingDate(dateRange, locale) {
    try {
        dateRange = toString(dateRange).trim();
        return (
            parseAccountingQuarter(dateRange) ||
            parseAccountingMonth(dateRange) ||
            parseAccountingYear(dateRange, locale) ||
            parseAccountingDay(dateRange, locale)
        );
    } catch {
        throw new Error(
            sprintf(
                _t(
                    `'%s' is not a valid period. Supported formats are "21/12/2022", "Q1/2022", "12/2022", and "2022".`
                ),
                dateRange
            )
        );
    }
}

const ODOO_FIN_ARGS = () => [
    arg("account_codes (string)", _t("The prefix of the accounts.")),
    arg(
        "date_range (string, date)",
        _t(`The date range. Supported formats are "21/12/2022", "Q1/2022", "12/2022", and "2022".`)
    ),
    arg("offset (number, default=0)", _t("Year offset applied to date_range.")),
    arg("company_id (number, optional)", _t("The company to target (Advanced).")),
    arg(
        "include_unposted (boolean, default=FALSE)",
        _t("Set to TRUE to include unposted entries.")
    ),
];

functionRegistry.add("ODOO.CREDIT", {
    description: _t("Get the total credit for the specified account(s) and period."),
    args: ODOO_FIN_ARGS(),
    category: "Odoo",
    returns: ["NUMBER"],
    computeValueAndFormat: function (
        accountCodes,
        dateRange,
        offset = { value: 0 },
        companyId = { value: null },
        includeUnposted = { value: false }
    ) {
        accountCodes = toString(accountCodes?.value)
            .split(",")
            .map((code) => code.trim())
            .sort();
        offset = toNumber(offset.value, this.locale);
        if (dateRange?.format) {
            dateRange = { ...dateRange };
            dateRange.value = formatValue(dateRange.value, {
                format: dateRange.format,
                locale: this.locale,
            });
        }
        dateRange = parseAccountingDate(dateRange?.value, this.locale);
        includeUnposted = toBoolean(includeUnposted.value);
        const value = this.getters.getAccountPrefixCredit(
            accountCodes,
            dateRange,
            offset,
            companyId.value,
            includeUnposted
        );
        const format = this.getters.getCompanyCurrencyFormat(companyId.value) || "#,##0.00";
        return { value, format };
    },
});

functionRegistry.add("ODOO.DEBIT", {
    description: _t("Get the total debit for the specified account(s) and period."),
    args: ODOO_FIN_ARGS(),
    category: "Odoo",
    returns: ["NUMBER"],
    computeValueAndFormat: function (
        accountCodes,
        dateRange,
        offset = { value: 0 },
        companyId = { value: null },
        includeUnposted = { value: false }
    ) {
        accountCodes = toString(accountCodes?.value)
            .split(",")
            .map((code) => code.trim())
            .sort();
        offset = toNumber(offset.value, this.locale);
        if (dateRange?.format) {
            dateRange = { ...dateRange };
            dateRange.value = formatValue(dateRange.value, {
                format: dateRange.format,
                locale: this.locale,
            });
        }
        dateRange = parseAccountingDate(dateRange?.value, this.locale);
        includeUnposted = toBoolean(includeUnposted.value);
        const value = this.getters.getAccountPrefixDebit(
            accountCodes,
            dateRange,
            offset,
            companyId.value,
            includeUnposted
        );
        const format = this.getters.getCompanyCurrencyFormat(companyId.value) || "#,##0.00";
        return { value, format };
    },
});

functionRegistry.add("ODOO.BALANCE", {
    description: _t("Get the total balance for the specified account(s) and period."),
    args: ODOO_FIN_ARGS(),
    category: "Odoo",
    returns: ["NUMBER"],
    computeValueAndFormat: function (
        accountCodes,
        dateRange,
        offset = { value: 0 },
        companyId = { value: null },
        includeUnposted = { value: false }
    ) {
        accountCodes = toString(accountCodes?.value)
            .split(",")
            .map((code) => code.trim())
            .sort();
        offset = toNumber(offset.value, this.locale);
        if (dateRange?.format) {
            dateRange = { ...dateRange };
            dateRange.value = formatValue(dateRange.value, {
                format: dateRange.format,
                locale: this.locale,
            });
        }
        dateRange = parseAccountingDate(dateRange?.value, this.locale);
        includeUnposted = toBoolean(includeUnposted.value);
        const value =
            this.getters.getAccountPrefixDebit(
                accountCodes,
                dateRange,
                offset,
                companyId.value,
                includeUnposted
            ) -
            this.getters.getAccountPrefixCredit(
                accountCodes,
                dateRange,
                offset,
                companyId.value,
                includeUnposted
            );
        const format = this.getters.getCompanyCurrencyFormat(companyId.value) || "#,##0.00";
        return { value, format };
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
    computeFormat: function () {
        return this.locale.dateFormat;
    },
    compute: function (date, companyId = null) {
        const startDate = this.getters.getFiscalStartDate(
            toJsDate(date, this.locale),
            companyId === null ? null : toNumber(companyId, this.locale)
        );
        return toNumber(startDate, this.locale);
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
    computeFormat: function () {
        return this.locale.dateFormat;
    },
    compute: function (date, companyId = null) {
        const endDate = this.getters.getFiscalEndDate(
            toJsDate(date, this.locale),
            companyId === null ? null : toNumber(companyId, this.locale)
        );
        return toNumber(endDate, this.locale);
    },
});

functionRegistry.add("ODOO.ACCOUNT.GROUP", {
    description: _t("Returns the account ids of a given group."),
    args: [arg("type (string)", _t("The account type (income, expense, asset_current,...)."))],
    category: "Odoo",
    returns: ["NUMBER"],
    compute: function (accountType) {
        const accountTypes = this.getters.getAccountGroupCodes(toString(accountType));
        return accountTypes.join(",");
    },
});
