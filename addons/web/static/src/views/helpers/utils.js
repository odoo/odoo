/** @odoo-module **/

/**
 * Parse the arch to check if is true or false
 * If the string is empyt, 0, False or false it's considered as false
 * The rest is considered as true
 *
 * @param {string} str
 * @returns {boolean}
 */
export function archParseBoolean(str) {
    return str !== "False" && str !== "false" && str !== "0" && str !== "";
}
