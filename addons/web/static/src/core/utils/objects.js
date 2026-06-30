/**
 * Shallow compares two objects.
 *
 * @template {unknown} T
 * @param {T} obj1
 * @param {T} obj2
 * @param {(a: T[keyof T], b: T[keyof T]) => boolean} [comparisonFn]
 */
export function shallowEqual(obj1, obj2, comparisonFn = (a, b) => a === b) {
    if (obj1 !== Object(obj1) || obj2 !== Object(obj2)) {
        return obj1 === obj2;
    }
    const obj1Keys = Reflect.ownKeys(obj1);
    return (
        obj1Keys.length === Reflect.ownKeys(obj2).length &&
        obj1Keys.every((key) => comparisonFn(obj1[key], obj2[key]))
    );
}

/**
 * Deeply compares two objects.
 *
 * @template {unknown} T
 * @param {T} obj1
 * @param {T} obj2
 */
export const deepEqual = (obj1, obj2) => shallowEqual(obj1, obj2, deepEqual);

/**
 * Deep copies an object. As it relies on JSON this function as some limitations
 * - no support for circular objects
 * - no support for specific classes, that will at best be lost and at worst crash (Map, Set etc...)
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
 * @param {...(K)} properties
 * @returns {Pick<T, K>}
 */
export function pick(object, ...properties) {
    return Object.fromEntries(
        properties.filter((prop) => prop in object).map((prop) => [prop, object[prop]])
    );
}

/**
 * Deeply merges two objects, recursively combining properties.
 * Works like the spread operator but will merge nested objects.
 *
 * This function doesn't merge arrays.
 *
 * @param {Object} target - The target object to merge into.
 * @param {Object} extension - The extension to apply.
 * @returns {Object} - The merged object.
 *
 * @example
 * const target = { a: 1, b: { c: 2 } };
 * const source = { a: 2, b: { d: 3 } };
 * const output = deepMerge(target, source);
 * // output => { a: 2, b: { c: 2, d: 3 } }
 */
export function deepMerge(target, extension) {
    if (!isObject(target) && !isObject(extension)) {
        return;
    }

    target = target || {};
    const output = Object.assign({}, target);
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
