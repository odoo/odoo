/** @odoo-module **/

/**
 * Follows the given related path starting from the given record, and returns
 * the resulting value, or undefined if a relation can't be followed because it
 * is undefined.
 *
 * @param {mail.model} record
 * @param {string} relatedPath field names, dot separated to follow relations
 * @returns {any}
 */
export function followRelations(record, relatedPath) {
    let target = record;
    for (const field of relatedPath.split('.')) {
        if (!target.constructor.__fieldMap[field]) {
            throw Error(`field(${field}) does not exist on ${target}`);
        }
        target = target[field];
        if (!target) {
            break;
        }
    }
    return target;
}
