/** @odoo-module **/

export function isBinarySize(value) {
    return /^\d+(\.\d*)? [^0-9]+$/.test(value);
}
