// @ts-check

import { helpers } from "@odoo/o-spreadsheet";

const { getFunctionsFromTokens } = helpers;

/**
 * @typedef {import("@odoo/o-spreadsheet").Token} Token
 * @typedef  {import("@spreadsheet/helpers/odoo_functions_helpers").OdooFunctionDescription} OdooFunctionDescription
 */

/**
 * @param {Token[]} tokens
 * @returns {number}
 */
export function getNumberOfAccountFormulas(tokens) {
    return getFunctionsFromTokens(tokens, ["ODOO.BALANCE", "ODOO.CREDIT", "ODOO.DEBIT", "ODOO.RESIDUAL", "ODOO.PARTNER.BALANCE", "ODOO.BALANCE.TAG"]).length;
}

/**
 * Get the first Account function description of the given formula.
 *
 * @param {Token[]} tokens
 * @returns {OdooFunctionDescription | undefined}
 */
export function getFirstAccountFunction(tokens) {
    return getFunctionsFromTokens(tokens, ["ODOO.BALANCE", "ODOO.CREDIT", "ODOO.DEBIT", "ODOO.RESIDUAL", "ODOO.PARTNER.BALANCE", "ODOO.BALANCE.TAG"])[0];
}
