// @ts-check

/** @module @web/services/currency - Currency lookup, formatting, and exchange rate fetching */

import { reactive } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";
import { formatFloat, humanNumber } from "@web/core/utils/format/numbers";
import { nbsp } from "@web/core/utils/format/strings";
import { user } from "@web/services/user";
import { session } from "@web/session";

/** @type {Record<number, {symbol: string, position: string, digits: [number, number]}>} */
export const currencies = session.currencies || {};
// to make sure code is reading currencies from here
delete session.currencies;

/**
 * Look up a currency definition by its database ID.
 * @param {number} id - res.currency record ID
 * @returns {{symbol: string, position: string, digits: [number, number]} | undefined}
 */
export function getCurrency(id) {
    return currencies[id];
}

/**
 * Fetch inverse exchange rates for all known currencies relative to the
 * active company's currency. Returns a reactive object that auto-updates
 * when the disk cache detects changes.
 * @returns {Promise<Record<number, number>>} currency id → inverse rate
 */
export async function getCurrencyRates() {
    /** @type {Record<number, number>} */
    const rates = reactive({});

    /**
     * @param {Array<{id: number, inverse_rate: number}>} records
     * @returns {Record<number, number>}
     */
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
 * @param {number} amount the value that should be formatted
 * @param {number} [currencyId] the id of the 'res.currency' to use
 * @param {any} [options] formatting options (data, noSymbol, humanReadable,
 *   minDigits, trailingZeros, digits)
 * @returns {string}
 */
export function formatCurrency(amount, currencyId, options = {}) {
    const currency = getCurrency(currencyId);

    const digits =
        options.digits !== undefined ? options.digits : currency && currency.digits;

    let formattedAmount;
    if (options.humanReadable) {
        formattedAmount = humanNumber(amount, {
            decimals: digits ? digits[1] : 2,
            minDigits: options.minDigits,
        });
    } else {
        formattedAmount = formatFloat(amount, {
            digits,
            minDigits: options.minDigits,
            trailingZeros: options.trailingZeros,
        });
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
