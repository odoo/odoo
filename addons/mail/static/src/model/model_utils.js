/** @odoo-module **/

/**
 * Follows the given related path starting from the given record, and returns
 * the resulting value, or undefined if a relation can't be followed because it
 * is undefined.
 *
 * @param {Record} record
 * @param {string[]} relatedPath Array of field names.
 * @returns {any}
 */
export function followRelations(record, relatedPath) {
    let target = record;
    for (const field of relatedPath) {
        target = target[field];
        if (!target) {
            break;
        }
    }
    return target;
}
