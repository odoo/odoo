/** @odoo-module **/

import { intersperse } from "@web/core/utils/strings";
import { localization } from "@web/core/l10n/localization";

/**
 * Inserts "thousands" separators in the provided number.
 *
 * @private
 * @param {string} string representing integer number
 * @returns {string}
 */
export function insertThousandsSep(number) {
    const { thousandsSep, grouping } = localization;
    const negative = number[0] === "-";
    number = negative ? number.slice(1) : number;
    return (negative ? "-" : "") + intersperse(number, grouping, thousandsSep);
}

/**
 * Returns the price formatted according to the selected l10n.
 *
 * @param {float} price
 */
export function priceToStr(price) {
    let precision = 2;
    const decimalPrecisionEl = document.querySelector(".decimal_precision");
    if (decimalPrecisionEl) {
        precision = parseInt(decimalPrecisionEl.dataset.precision);
    }
    const formatted = _.str.sprintf(`%.${precision}f`, price).split(".");
    formatted[0] = insertThousandsSep(formatted[0]);
    return formatted.join(localization.decimalPoint);
}
