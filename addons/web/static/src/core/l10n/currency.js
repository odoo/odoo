/** @odoo-module **/

import { formatFloat, humanNumber } from "./numbers";

/**
 * Formats a value as a currency.
 *
 * @param {number|false} value currency value number
 * @param {string} cid currency id
 * @param {Object} [options={}] formatting options
 * @param {boolean} [options.noSymbol] this currency has not a sympbol
 * @param {boolean} [options.humanReadable] this currency needs to be human readable
 * @param {[number, number]} [options.digits]
 *    the number of digits that should be used, instead of the default digits precision in the field.
 *    Note: if the currency defines a precision, the currency's one is used.
 *    The first number is always ignored (legacy constraint)
 * @returns The formatted currency
 */
export function formatCurrency(value, cid, options = {}) {
    if (value === false) {
        return "";
    }
    const currency = odoo.session_info.currencies[cid];
    const { noSymbol } = options || {};
    const digits = (currency && currency.digits) || options.digits;

    const formatted = options.humanReadable
        ? humanNumber(value)
        : formatFloat(value, { precision: digits && digits[1] });
    if (!currency || noSymbol) {
        return formatted;
    }
    if (currency.position === "after") {
        return `${formatted} ${currency.symbol}`;
    } else {
        return `${currency.symbol} ${formatted}`;
    }
}
