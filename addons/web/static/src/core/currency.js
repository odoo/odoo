import { formatFloat, humanNumber } from "@web/core/utils/numbers";
import { session } from "@web/session";
import { nbsp } from "@web/core/utils/strings";

export const currencies = session.currencies || {};
// to make sure code is reading currencies from here
delete session.currencies;

export function getCurrency(id) {
    return currencies[id];
}

/**
 * Returns a string representing a monetary value. The result takes into account
 * the user settings (to display the correct decimal separator, currency, ...).
 *
 * @param {number} value the value that should be formatted
 * @param {number} [currencyId] the id of the 'res.currency' to use
 * @param {Object} [options]
 *   additional options to override the values in the python description of the
 *   field.
 * @param {Object} [options.data] a mapping of field names to field values,
 *   required with options.currencyField
 * @param {boolean} [options.noSymbol] this currency has not a sympbol
 * @param {boolean} [options.humanReadable] if true, large numbers are formatted
 *   to a human readable format.
 * @param {[number, number]} [options.digits] the number of digits that should
 *   be used, instead of the default digits precision in the field.  The first
 *   number is always ignored (legacy constraint)
 * @returns {string}
 */
export function formatCurrency(amount, currencyId, options = {}) {
    const currency = getCurrency(currencyId);

    const digits = (options.digits !== undefined)? options.digits : (currency && currency.digits)

    let formattedAmount;
    if (options.humanReadable) {
        formattedAmount = humanNumber(amount, { decimals: digits ? digits[1] : 2 });
    } else {
        formattedAmount = formatFloat(amount, { digits, minDigits: options.minDigits});
    }

    if (!currency || options.noSymbol) {
        return formattedAmount;
    }
    const formatted = [currency.symbol, formattedAmount];
    if (currency.position === "after") {
        formatted.reverse();
    }
    return formatted.join(nbsp);
}
