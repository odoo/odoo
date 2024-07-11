/** @odoo-module **/

import { helpers } from "@odoo/o-spreadsheet";

const { createCurrencyFormat } = helpers;

/**
 * @param {object} currency
 * @returns {string}
 */
export function createDefaultCurrencyFormat(currency) {
    return createCurrencyFormat({
        symbol: currency.symbol,
        position: currency.position,
        decimalPlaces: currency.decimalPlaces,
    });
}
