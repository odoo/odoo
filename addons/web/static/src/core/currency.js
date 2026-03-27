import { reactive } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";
import { user } from "@web/core/user";
import { formatFloat, humanNumber } from "@web/core/utils/numbers";
import { nbsp } from "@web/core/utils/strings";
import { session } from "@web/session";

export const currencies = session.currencies || {};
// to make sure code is reading currencies from here
delete session.currencies;

export function getCurrency(id) {
    return currencies[id];
}

export async function getCurrencyRates() {
    const rates = reactive({});

    function recordsToRates(records) {
        return Object.fromEntries(records.map((r) => [r.id, r.inverse_rate]));
    }

    const model = "res.currency";
    const method = "read";
    const url = `/web/dataset/call_kw/${model}/${method}`;
    const context = {
        ...user.context,
        to_currency: user.activeCompany.currency_id,
    };
    const params = {
        model,
        method,
        args: [Object.keys(currencies).map(Number), ["inverse_rate"]],
        kwargs: { context },
    };
    const records = await rpc(url, params, {
        cache: {
            type: "disk",
            update: "once",
            callback: (records, hasChanged) => {
                if (hasChanged) {
                    Object.assign(rates, recordsToRates(records));
                }
            },
        },
    });
    Object.assign(rates, recordsToRates(records));
    return rates;
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
 * @param {number} [options.minDigits] see @humanNumber
 * @param {boolean} [options.trailingZeros] if false, numbers will have zeros
 *  to the right of the last non-zero digit hidden
 * @param {[number, number]} [options.digits] the number of digits that should
 *   be used, instead of the default digits precision in the field.  The first
 *   number is always ignored (legacy constraint)
 * @param {number} [options.minDigits] the minimum number of decimal digits to display.
 *   Displays maximum 6 decimal places if no precision is provided.
 * @returns {string}
 */
export function formatCurrency(amount, currencyId, options = {}) {
    const currency = getCurrency(currencyId);

    const digits = (options.digits !== undefined)? options.digits : (currency && currency.digits)

    let formattedAmount;
    if (options.humanReadable) {
        formattedAmount = humanNumber(amount, {
            decimals: digits ? digits[1] : 2,
            minDigits: options.minDigits,
        });
    } else {
        formattedAmount = formatFloat(amount, { digits, minDigits: options.minDigits, trailingZeros: options.trailingZeros });
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
