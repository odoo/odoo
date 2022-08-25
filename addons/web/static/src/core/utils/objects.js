/** @odoo-module **/

/**
 * Shallow compares two objects.
 */
export function shallowEqual(obj1, obj2) {
    const obj1Keys = Object.keys(obj1);
    return (
        obj1Keys.length === Object.keys(obj2).length &&
        obj1Keys.every((key) => obj1[key] === obj2[key])
    );
}

/**
 * Deep copies an object. As it relies on JSON this function as some limitations
 * - no support for circular objects
 * - no support for specific classes, that will at best be lost and at worst crash (Map, Set etc...)
 * @param  {Object} An object that is fully JSON stringifiable
 * @return {Object}
 */
export function deepCopy(obj) {
    return JSON.parse(JSON.stringify(obj));
}

/**
 * @template {T}
 * @param {T} object
 * @param {...(keyof T)} properties
 * @returns {Partial<T>}
 */
export function pick(object, ...properties) {
    return Object.fromEntries(
        properties.filter((prop) => prop in object).map((prop) => [prop, object[prop]])
    );
}
