/** @odoo-module **/

/**
 * Shallow compares two objects.
 *
 * @param {Record<string, any>} obj1
 * @param {Record<string, any>} obj2
 * @returns {boolean}
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
 * @template T
 * @param {T} obj An object that is fully JSON stringifiable
 * @return {T}
 */
export function deepCopy(obj) {
    return JSON.parse(JSON.stringify(obj));
}

/**
 * Returns a shallow copy of object with every property in properties removed
 * if present in object.
 *
 * @template T
 * @template {keyof T} K
 * @param {T} object
 * @param {K[]} properties
 */
export function omit(object, ...properties) {
    /** @type {Omit<T, K>} */
    const result = {};
    const propertiesSet = new Set(properties);
    for (const key in object) {
        if (!propertiesSet.has(key)) {
            result[key] = object[key];
        }
    }
    return result;
}

/**
 * @template T
 * @template {keyof T} K
 * @param {T} object
 * @param {K[]} properties
 * @returns {Pick<T, K>}
 */
export function pick(object, ...properties) {
    return Object.fromEntries(
        properties.filter((prop) => prop in object).map((prop) => [prop, object[prop]])
    );
}
