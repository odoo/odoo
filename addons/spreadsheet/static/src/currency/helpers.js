/** @ts-check */

import { helpers } from "@odoo/o-spreadsheet";
const { createCurrencyFormat } = helpers;

/**
 * @typedef Currency
 * @property {string} name
 * @property {string} code
 * @property {string} symbol
 * @property {number} decimalPlaces
 * @property {"before" | "after"} position
 */

/**
 * Return the currency cleaned from useless info and from the `code` field to be used to generate
 * a default currency format.
 *
 * @param {Currency | undefined} currency
 * @returns {object}
 */
export function createDefaultCurrency(currency) {
    if (!currency) {
        return undefined;
    }
    return {
        symbol: currency.symbol,
        position: currency.position,
        decimalPlaces: currency.decimalPlaces,
    };
}

/**
 * @param {Currency | undefined} currency
 * @returns {string | undefined}
 */
export function computeFormatFromCurrency(currency) {
    const defaultCurrency = createDefaultCurrency(currency);
    return defaultCurrency ? createCurrencyFormat(defaultCurrency) : undefined;
}
