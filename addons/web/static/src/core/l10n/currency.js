/** @odoo-module **/

import { formatFloat, humanNumber, parseFloat, InvalidNumberError } from "./numbers";

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

/**
 * Try to extract a monetary value from a string. The localization is considered in the process.
 * The monetary value can have the formats sym$&nbsp;float, float$&nbsp;sym or float
 * where $&nbsp; is a non breaking space and sym is a currency symbol.
 * If a symbol is found it must correspond to the default currency symbol or to the
 * symbol of the currency whose id is passed in options.
 *
 * @param {string} value
 * @param {Object} [options={}]
 * @param {number} [options.currencyId]
 * @returns {number} float
 */
export function parseCurrency(value, options = {}) {
    let values = value.split("&nbsp;");
    if (values.length === 1) {
        return parseFloat(value);
    }
    let currency;
    if (options.currencyId) {
        currency = odoo.session_info.currencies[options.currencyId];
    } else {
        currency = Object.values(odoo.session_info.currencies)[0];
    }
    const symbolIndex = values.findIndex((v) => v === currency.symbol);
    if (symbolIndex === -1) {
        throw new InvalidNumberError(`"${value}" is not a correct number`);
    }
    values.splice(symbolIndex, 1);
    if (values.length !== 1) {
        throw new InvalidNumberError(`"${value}" is not a correct number`);
    }
    return parseFloat(values[0]);
}
