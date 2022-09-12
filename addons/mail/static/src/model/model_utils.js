/** @odoo-module **/

// As the split operation can be quite expensive, the splitted form of related
// paths is stored to avoid recomputing it every time.
const splittedPathRegistry = new Map();

/**
 * Follows the given related path starting from the given record, and returns
 * the resulting value, or undefined if a relation can't be followed because it
 * is undefined.
 *
 * @param {Record} record
 * @param {string} relatedPath field names, dot separated to follow relations
 * @returns {any}
 */
export function followRelations(record, relatedPath) {
    let target = record;
    let fieldsToFollow;
    if (splittedPathRegistry.has(relatedPath)) {
        fieldsToFollow = splittedPathRegistry.get(relatedPath);
    } else {
        fieldsToFollow = relatedPath.split('.');
        splittedPathRegistry.set(relatedPath, fieldsToFollow);
    }
    for (const field of fieldsToFollow) {
        if (!target.constructor.__fieldMap.has(field)) {
            throw Error(`field(${field}) does not exist on ${target}`);
        }
        target = target[field];
        if (!target) {
            break;
        }
    }
    return target;
}
