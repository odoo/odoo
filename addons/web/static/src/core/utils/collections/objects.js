// @ts-check

/** @module @web/core/utils/collections/objects - Object helpers: deepEqual, deepCopy, pick, omit, deepMerge */

/**
 * Shallow compares two objects.
 *
 * @template T
 * @param {T} obj1
 * @param {T} obj2
 * @param {(a: any, b: any) => boolean} [comparisonFn]
 * @returns {boolean}
 */
export function shallowEqual(obj1, obj2, comparisonFn = (a, b) => a === b) {
    if (obj1 !== Object(obj1) || obj2 !== Object(obj2)) {
        return obj1 === obj2;
    }
    const o1 = /** @type {any} */ (obj1);
    const o2 = /** @type {any} */ (obj2);
    const obj1Keys = Reflect.ownKeys(o1);
    return (
        obj1Keys.length === Reflect.ownKeys(o2).length &&
        obj1Keys.every((key) => comparisonFn(o1[key], o2[key]))
    );
}

/**
 * Deeply compares two objects.
 *
 * @param {unknown} obj1
 * @param {unknown} obj2
 * @returns {boolean}
 */
export const deepEqual = (obj1, obj2) => shallowEqual(obj1, obj2, deepEqual);

/**
 * Deep copies an object. As it relies on JSON this function has some limitations:
 * - no support for circular objects
 * - no support for specific classes, that will at best be lost and at worst crash (Map, Set etc.)
 * @template T
 * @param {T} object An object that is fully JSON stringifiable
 * @return {T}
 */
export function deepCopy(object) {
    return object && JSON.parse(JSON.stringify(object));
}

/**
 * Returns whether the given value is an object, i.e. an instance of the `Object`
 * class or of one of its direct subclass.
 *
 * Note: this may wrongly validate any object implementing a modified `toString`
 * explicitly returning `"[object Object]"`.
 *
 * @param {unknown} value
 * @returns {boolean}
 * @example
 *  // true
 *  isObject({ a: 1 });
 *  isObject(Object.create(null));
 * @example
 *  // false
 *  isObject([1, 2, 3]);
 *  isObject(new Map([["a", 1]]));
 */
export function isObject(value) {
    return Object.prototype.toString.call(value) === "[object Object]";
}

/**
 * Returns a shallow copy of object with every property in properties removed
 * if present in object.
 *
 * @template T
 * @template {keyof T} K
 * @param {T} object
 * @param {...(K)} properties
 * @returns {Omit<T, K>}
 */
export function omit(object, ...properties) {
    /** @type {any} */
    const result = {};
    const propertiesSet = new Set(properties);
    for (const key in object) {
        if (!propertiesSet.has(/** @type {any} */ (key))) {
            result[key] = object[key];
        }
    }
    return result;
}

/**
 * @template T
 * @template {keyof T} K
 * @param {T} object
 * @param {...(K)} properties
 * @returns {Pick<T, K>}
 */
export function pick(object, ...properties) {
    return /** @type {Pick<T, K>} */ (
        Object.fromEntries(
            properties
                .filter((prop) => prop in /** @type {any} */ (object))
                .map((prop) => [prop, /** @type {any} */ (object)[prop]]),
        )
    );
}

/**
 * Deeply merges two values, recursively combining plain-object properties.
 * Non-object values (primitives, arrays, functions) follow "extension wins"
 * semantics: `extension` is returned as-is, unless it is `undefined`, in
 * which case `target` is returned. Arrays are not deep-merged; `extension`
 * replaces `target` entirely for array values.
 *
 * @param {any} target - The base value.
 * @param {any} extension - The value to merge on top of target.
 * @returns {any} - The merged result.
 *
 * @example
 * const target = { a: 1, b: { c: 2 } };
 * const source = { a: 2, b: { d: 3 } };
 * const output = deepMerge(target, source);
 * // output => { a: 2, b: { c: 2, d: 3 } }
 */
export function deepMerge(target, extension) {
    if (!isObject(target) && !isObject(extension)) {
        // Neither side is a plain object — nothing to merge.
        return undefined;
    }

    target = target || {};
    const output = { ...target };
    if (isObject(extension)) {
        for (const key of Reflect.ownKeys(extension)) {
            if (
                key in target &&
                isObject(extension[key]) &&
                !Array.isArray(extension[key]) &&
                typeof extension[key] !== "function"
            ) {
                output[key] = deepMerge(target[key], extension[key]);
            } else {
                Object.assign(output, { [key]: extension[key] });
            }
        }
    }

    return output;
}
