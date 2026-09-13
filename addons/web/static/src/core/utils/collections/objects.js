// @ts-check
/** @odoo-module native */

import { toRaw } from "@odoo/owl";

/**
 * @param {any} a
 * @param {any} b
 * @returns {boolean}
 */
export function sameValue(a, b) {
    return a === b || (Number.isNaN(a) && Number.isNaN(b));
}

/**
 * @param {unknown} obj1
 * @param {unknown} obj2
 * @param {(a: any, b: any) => boolean} [comparisonFn]
 * @returns {boolean}
 */
export function shallowEqual(obj1, obj2, comparisonFn = sameValue) {
    if (obj1 !== Object(obj1) || obj2 !== Object(obj2)) {
        return obj1 === obj2;
    }
    const o1 = /** @type {any} */ (obj1);
    const o2 = /** @type {any} */ (obj2);
    const obj1Keys = Reflect.ownKeys(o1);
    return (
        obj1Keys.length === Reflect.ownKeys(o2).length &&
        obj1Keys.every(
            (key) => Object.hasOwn(o2, key) && comparisonFn(o1[key], o2[key]),
        )
    );
}

/**
 * @param {unknown} obj1
 * @param {unknown} obj2
 * @returns {boolean}
 */
export function deepEqual(obj1, obj2) {
    return _deepEqual(obj1, obj2, new WeakMap());
}

/**
 * @param {any} a
 * @param {any} b
 * @param {WeakMap<object, WeakSet<object>>} seen
 * @returns {boolean}
 */
function _deepEqual(a, b, seen) {
    if (sameValue(a, b)) {
        return true;
    }
    if (a === null || b === null || typeof a !== "object" || typeof b !== "object") {
        return false;
    }
    let counterparts = seen.get(a);
    if (counterparts?.has(b)) {
        return true;
    }
    if (!counterparts) {
        counterparts = new WeakSet();
        seen.set(a, counterparts);
    }
    counterparts.add(b);
    const equal = _deepEqualInner(a, b, seen);
    if (!equal) {
        counterparts.delete(b);
    }
    return equal;
}

/**
 * @param {any} a
 * @param {any} b
 * @param {WeakMap<object, WeakSet<object>>} seen
 * @returns {boolean}
 */
function _deepEqualInner(a, b, seen) {
    if (a instanceof Date || b instanceof Date) {
        return a instanceof Date && b instanceof Date && a.getTime() === b.getTime();
    }
    if (a instanceof RegExp || b instanceof RegExp) {
        return (
            a instanceof RegExp &&
            b instanceof RegExp &&
            a.source === b.source &&
            a.flags === b.flags
        );
    }
    const aIsArray = Array.isArray(a);
    if (aIsArray || Array.isArray(b)) {
        if (!aIsArray || !Array.isArray(b) || a.length !== b.length) {
            return false;
        }
        for (let i = 0; i < a.length; i++) {
            if (!_deepEqual(a[i], b[i], seen)) {
                return false;
            }
        }
        return true;
    }
    if (a instanceof Map || b instanceof Map) {
        if (!(a instanceof Map) || !(b instanceof Map) || a.size !== b.size) {
            return false;
        }
        for (const [key, value] of a) {
            if (!b.has(key) || !_deepEqual(value, b.get(key), seen)) {
                return false;
            }
        }
        return true;
    }
    if (a instanceof Set || b instanceof Set) {
        if (!(a instanceof Set) || !(b instanceof Set) || a.size !== b.size) {
            return false;
        }
        const unmatched = new Set(b);
        for (const av of a) {
            if (unmatched.delete(av)) {
                continue;
            }
            let found = false;
            for (const bv of unmatched) {
                if (_deepEqual(av, bv, seen)) {
                    unmatched.delete(bv);
                    found = true;
                    break;
                }
            }
            if (!found) {
                return false;
            }
        }
        return true;
    }

    const aKeys = Reflect.ownKeys(a);
    if (aKeys.length !== Reflect.ownKeys(b).length) {
        return false;
    }
    return aKeys.every(
        (key) =>
            Object.prototype.hasOwnProperty.call(b, key) &&
            _deepEqual(a[key], b[key], seen),
    );
}

/**
 * @template T
 * @param {T} value
 * @param {WeakMap<object, object>} [seen]
 * @returns {T}
 */
export function toRawDeep(value, seen = new WeakMap()) {
    if (value === null || typeof value !== "object") {
        return value;
    }
    const raw = toRaw(value);
    if (seen.has(raw)) {
        return /** @type {any} */ (seen.get(raw));
    }
    if (Array.isArray(raw)) {
        /** @type {any[]} */
        const out = [];
        seen.set(raw, out);
        for (let i = 0; i < raw.length; i++) {
            out[i] = toRawDeep(raw[i], seen);
        }
        return /** @type {any} */ (out);
    }
    const proto = Object.getPrototypeOf(raw);
    if (proto === Object.prototype || proto === null) {
        /** @type {Record<string, any>} */
        const out = proto === null ? Object.create(null) : {};
        seen.set(raw, out);
        for (const k of Object.keys(raw)) {
            out[k] = toRawDeep(/** @type {any} */ (raw)[k], seen);
        }
        return /** @type {any} */ (out);
    }
    if (raw instanceof Map) {
        /** @type {Map<any, any>} */
        const out = new Map();
        seen.set(raw, out);
        for (const [k, v] of raw) {
            out.set(toRawDeep(k, seen), toRawDeep(v, seen));
        }
        return /** @type {any} */ (out);
    }
    if (raw instanceof Set) {
        /** @type {Set<any>} */
        const out = new Set();
        seen.set(raw, out);
        for (const v of raw) {
            out.add(toRawDeep(v, seen));
        }
        return /** @type {any} */ (out);
    }
    return /** @type {any} */ (raw);
}

/**
 * @template T
 * @param {T} object
 * @return {T}
 */
export function deepCopy(object) {
    if (!object) {
        return object;
    }
    try {
        return structuredClone(object);
    } catch {
        try {
            return structuredClone(toRawDeep(object));
        } catch (error) {
            const copy = JSON.parse(JSON.stringify(toRawDeep(object)));
            console.warn(
                "deepCopy fell back to JSON and may have dropped keys " +
                    "(functions, symbols, undefined) from the result:",
                error,
            );
            return copy;
        }
    }
}

/**
 * @param {unknown} value
 * @returns {boolean}
 */
export function isObject(value) {
    return Object.prototype.toString.call(value) === "[object Object]";
}

/**
 * Numeric keys and their canonical string spellings address the same property.
 * Noncanonical strings such as "01" remain distinct from numeric keys.
 * @template {PropertyKey} K
 * @typedef {K extends number ? K | `${K}`
 *  : K extends `${infer N extends number}` ? `${N}` extends K ? K | N : K
 *  : K} PropertyKeyAliases
 */

/**
 * @template {Record<string, any>} T
 * @template {PropertyKey[]} Keys
 * @param {T} object
 * @param {Keys} properties
 * @returns {Omit<T, PropertyKeyAliases<Keys[number]>>}
 */
export function omit(object, ...properties) {
    /** @type {any} */
    const result = {};
    /** @type {Set<PropertyKey>} */
    const excluded = new Set(
        properties.map((key) => (typeof key === "number" ? String(key) : key)),
    );
    const source = /** @type {Record<PropertyKey, any>} */ (object);
    for (const key of Object.keys(source)) {
        if (!excluded.has(key)) {
            result[key] = source[key];
        }
    }
    for (const symbol of Object.getOwnPropertySymbols(source)) {
        if (
            !excluded.has(symbol) &&
            Object.prototype.propertyIsEnumerable.call(source, symbol)
        ) {
            result[symbol] = source[symbol];
        }
    }
    return result;
}

/**
 * @param {any} object
 * @param {PropertyKey} property
 * @returns {boolean}
 */
function hasPropertyBelowObject(object, property) {
    for (
        let current = object;
        current !== null && current !== undefined && current !== Object.prototype;
        current = Object.getPrototypeOf(current)
    ) {
        if (Object.hasOwn(current, property)) {
            return true;
        }
    }
    return false;
}

/**
 * @template T
 * @template {PropertyKey[]} Keys
 * @param {T} object
 * @param {Keys} properties
 * @returns {Pick<T, Extract<PropertyKeyAliases<Keys[number]>, keyof T>> & Partial<Record<Exclude<Keys[number], PropertyKeyAliases<keyof T>>, unknown>>}
 */
export function pick(object, ...properties) {
    /** @type {any} */
    const result = {};
    const source = /** @type {Record<PropertyKey, any>} */ (object);
    for (const property of properties) {
        if (hasPropertyBelowObject(source, /** @type {PropertyKey} */ (property))) {
            result[property] = source[/** @type {PropertyKey} */ (property)];
        }
    }
    return result;
}

/**
 * @param {Record<PropertyKey, any>} output
 * @param {PropertyKey} key
 * @param {any} value
 */
function defineOwn(output, key, value) {
    Object.defineProperty(output, key, {
        value,
        writable: true,
        enumerable: true,
        configurable: true,
    });
}

/**
 * @param {any} target
 * @param {any} extension
 * @returns {any}
 */
export function deepMerge(target, extension) {
    if (!isObject(target) && !isObject(extension)) {
        return extension !== undefined ? extension : target;
    }

    target = Object(target || {});
    /** @type {Record<PropertyKey, any>} */
    const output = {};
    for (const key of Reflect.ownKeys(target)) {
        if (Object.getOwnPropertyDescriptor(target, key)?.enumerable) {
            defineOwn(output, key, target[key]);
        }
    }
    if (isObject(extension)) {
        for (const key of Reflect.ownKeys(extension)) {
            if (!Object.getOwnPropertyDescriptor(extension, key)?.enumerable) {
                continue;
            }
            const extensionValue = extension[key];
            if (extensionValue === undefined) {
                continue;
            }
            const targetValue = Object.hasOwn(target, key) ? target[key] : undefined;
            defineOwn(
                output,
                key,
                isObject(targetValue) && isObject(extensionValue)
                    ? deepMerge(targetValue, extensionValue)
                    : extensionValue,
            );
        }
    }

    return output;
}
