/** @odoo-module **/

import helper from '@stock_barcode/../tests/tours/tour_helper_stock_barcode';

/**
 * Checks the line is linked to the given picking.
 *
 * @param {HTMLElement|Integer} lineOrIndex
 * @param {string} pickingName
 */
helper.assertLineBelongTo = (lineOrIndex, pickingName) => {
    const line = helper._getLineOrFail(lineOrIndex, "Can't check line's picking");
    const pickingLabel = line.querySelector('.o_picking_label').innerText;
    helper.assert(pickingLabel, pickingName, "Wrong picking");
};

/**
 * Checks all lines are linked to the given picking.
 *
 * @param {HTMLElement[]} lines
 * @param {string} pickingName
 */
helper.assertLinesBelongTo = (lines, pickingName) => {
    lines.forEach(line => helper.assertLineBelongTo(line, pickingName));
};

export default helper;
