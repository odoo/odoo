import { _t } from "@web/core/l10n/translation";
import { formatFloat, roundPrecision } from "@web/core/utils/numbers";

/** Enterprise odoo.tools.misc.ROUNDING_UNIT_CHARS */
export const ROUNDING_UNIT_CHARS = {
    thousands: "k",
    lakhs: "L",
    millions: "M",
};

/** Enterprise account_reports.CURRENCIES_USING_LAKH */
export const CURRENCIES_USING_LAKH = new Set([
    "AFN",
    "BDT",
    "INR",
    "MMK",
    "NPR",
    "PKR",
    "LKR",
]);

/** Enterprise formatLang rounding_unit_mapping */
export const ROUNDING_DIVISORS = {
    decimals: 1,
    units: 1,
    thousands: 1e3,
    lakhs: 1e5,
    millions: 1e6,
};

/**
 * Mirror account.report._get_rounding_unit_names (dropdown labels only).
 * @param {string} currencySymbol
 * @param {string} [currencyName]
 */
export function getRoundingUnitNames(currencySymbol, currencyName) {
    const names = {
        decimals: `.${currencySymbol}`,
        units: `${currencySymbol}`,
        thousands: `k${currencySymbol}`,
        millions: `M${currencySymbol}`,
    };
    if (CURRENCIES_USING_LAKH.has(currencyName)) {
        return {
            decimals: names.decimals,
            units: names.units,
            thousands: names.thousands,
            lakhs: `L${currencySymbol}`,
            millions: names.millions,
        };
    }
    return names;
}

/**
 * Format a report amount like Enterprise formatLang(..., rounding_unit=..., no currency_obj).
 * Single-currency Balance Sheet cells have no currency symbol; thousands/lakhs/millions
 * append k / L / M after HALF-UP rounding.
 *
 * @param {number} amount
 * @param {string} roundingUnit
 * @param {number} [decimalPlaces=2]
 * @returns {string}
 */
export function formatReportAmount(amount, roundingUnit, decimalPlaces = 2) {
    if (amount === null || amount === undefined || amount === false) {
        return "";
    }
    const unit = ROUNDING_DIVISORS[roundingUnit] ? roundingUnit : "decimals";
    const digits = unit === "decimals" ? decimalPlaces : 0;
    let value = amount / (ROUNDING_DIVISORS[unit] || 1);
    const precision = digits === 0 ? 1 : Math.pow(10, -digits);
    value = roundPrecision(value, precision, "HALF-UP");
    // Enterprise _is_value_zero / -0.0 → 0.0
    if (Object.is(value, -0) || value === 0) {
        value = 0;
    }
    let formatted = formatFloat(value, {
        digits: [16, digits],
        trailingZeros: true,
    });
    const unitChar = ROUNDING_UNIT_CHARS[unit];
    if (unitChar) {
        formatted = `${formatted}${unitChar}`;
    }
    return formatted;
}

/** Keep for callers that only need the scaled number (no display). */
export function roundForUnit(amount, roundingUnit) {
    const divisor = ROUNDING_DIVISORS[roundingUnit] || 1;
    return amount / divisor;
}

/** Enterprise AccountReportFilters.roundingUnitName */
export function roundingUnitLabel(roundingUnit, names) {
    return _t("In %s", names[roundingUnit] || names.decimals);
}
