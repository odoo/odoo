/** @odoo-module **/

export * from '@stock_barcode/../tests/tours/tour_helper_stock_barcode';
import {assert, _getLineOrFail} from '@stock_barcode/../tests/tours/tour_helper_stock_barcode';

/**
 * Checks the line is linked to the given picking.
 *
 * @param {HTMLElement|Integer} lineOrIndex
 * @param {string} pickingName
 */
export function assertLineBelongTo(lineOrIndex, pickingName) {
    const line = _getLineOrFail(lineOrIndex, "Can't check line's picking");
    const pickingLabel = line.querySelector('.o_picking_label').innerText;
    assert(pickingLabel, pickingName, "Wrong picking");
}

/**
 * Checks all lines are linked to the given picking.
 *
 * @param {HTMLElement[]} lines
 * @param {string} pickingName
 */
export function assertLinesBelongTo(lines, pickingName) {
    lines.forEach(line => assertLineBelongTo(line, pickingName));
}
