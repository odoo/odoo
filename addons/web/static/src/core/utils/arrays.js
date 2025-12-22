import { shallowEqual as _shallowEqual } from "./objects";

/**
 * @template T
 * @template {string | number | symbol} K
 * @typedef {keyof T | ((item: T) => K)} Criterion
 */

/**
 * Same values returned as those returned by cartesian function for case n = 0
 * and n > 1. For n = 1, brackets are put around the unique parameter elements.
 *
 * @template T
 * @param {...T[]} args
 * @returns {T[][]}
 */
function _cartesian(...args) {
    if (args.length === 0) {
        return [undefined];
    }
    const firstArray = args.shift().map((elem) => [elem]);
    if (args.length === 0) {
        return firstArray;
    }
    const result = [];
    const productOfOtherArrays = _cartesian(...args);
    for (const array of firstArray) {
        for (const tuple of productOfOtherArrays) {
            result.push([...array, ...tuple]);
        }
    }
    return result;
}

/**
 * Helper function returning an extraction handler to use on array elements to
 * return a certain attribute or mutated form of the element.
 *
 * @private
 * @template T
 * @template {string | number | symbol} K
 * @param {Criterion<T, K>} [criterion]
 * @returns {(element: T) => any}
 */
function _getExtractorFrom(criterion) {
    if (criterion) {
        switch (typeof criterion) {
            case "string":
                return (element) => element[criterion];
            case "function":
                return criterion;
            default:
                throw new Error(
                    `Expected criterion of type 'string' or 'function' and got '${typeof criterion}'`
                );
        }
    } else {
        return (element) => element;
    }
}

/**
 * Returns an array containing either:
 * - the elements contained in the given iterable OR
 * - the given element if it is not an iterable
 *
 * @template T
 * @param {T | Iterable<T>} [value]
 * @returns {T[]}
 */
export function ensureArray(value) {
    return isIterable(value) ? [...value] : [value];
}

/**
 * Returns the array of elements contained in both arrays.
 *
 * @template T
 * @param {Iterable<T>} iter1
 * @param {Iterable<T>} iter2
 * @returns {T[]}
 */
export function intersection(iter1, iter2) {
    const set2 = new Set(iter2);
    return unique(iter1).filter((v) => set2.has(v));
}

/**
 * Returns whether the given value is an iterable object (excluding strings).
 *
 * @param {unknown} value
 */
export function isIterable(value) {
    return Boolean(value && typeof value === "object" && value[Symbol.iterator]);
}

/**
 * Returns an object holding different groups defined by a given criterion
 * or a default one. Each group is a subset of the original given list.
 * The given criterion can either be:
 * - a string: a property name on the list elements which value will be the
 * group name,
 * - a function: a handler that will return the group name from a given
 * element.
 *
 * @template T
 * @template {string | number | symbol} K
 * @param {Iterable<T>} iterable
 * @param {Criterion<T, K>} [criterion]
 * @returns {Record<K, T[]>}
 */
export function groupBy(iterable, criterion) {
    const extract = _getExtractorFrom(criterion);
    /** @type {Partial<Record<K, T[]>>} */
    const groups = {};
    for (const element of iterable) {
        const group = String(extract(element));
        if (!(group in groups)) {
            groups[group] = [];
        }
        groups[group].push(element);
    }
    return groups;
}

/**
 * Return a shallow copy of a given array sorted by a given criterion or a default one.
 * The given criterion can either be:
 * - a string: a property name on the array elements returning the sortable primitive
 * - a function: a handler that will return the sortable primitive from a given element.
 * The default order is ascending ('asc'). It can be modified by setting the extra param 'order' to 'desc'.
 *
 * @template T
 * @template {string | number | symbol} K
 * @param {Iterable<T>} iterable
 * @param {Criterion<T, K>} [criterion]
 * @param {"asc" | "desc"} [order="asc"]
 * @returns {T[]}
 */
export function sortBy(iterable, criterion, order = "asc") {
    const extract = _getExtractorFrom(criterion);
    return [...iterable].sort((elA, elB) => {
        const a = extract(elA);
        const b = extract(elB);
        let result;
        if (isNaN(a) && isNaN(b)) {
            result = a > b ? 1 : a < b ? -1 : 0;
        } else {
            result = a - b;
        }
        return order === "asc" ? result : -result;
    });
}

/**
 * Returns an array containing all the elements of arrayA
 * that are not in arrayB and vice-versa.
 *
 * @template T
 * @param {Iterable<T>} iter1
 * @param {Iterable<T>} iter2
 * @returns {T[]} an array containing all the elements of iter1
 * that are not in iter2 and vice-versa.
 */
export function symmetricalDifference(iter1, iter2) {
    const array1 = [...iter1];
    const array2 = [...iter2];
    return [
        ...array1.filter((value) => !array2.includes(value)),
        ...array2.filter((value) => !array1.includes(value)),
    ];
}

/**
 * Returns the product of any number n of arrays.
 * The internal structures of their elements is preserved.
 * For n = 1, no brackets are put around the unique parameter elements
 * For n = 0, [undefined] is returned since it is the unit
 * of the cartesian product (up to isomorphism).
 *
 * @template T
 * @param {...T[]} args
 * @returns {T[] | T[][]}
 */
export function cartesian(...args) {
    if (args.length === 0) {
        return [undefined];
    } else if (args.length === 1) {
        return args[0];
    } else {
        return _cartesian(...args);
    }
}

export const shallowEqual = _shallowEqual;

/**
 * Returns all initial sections of a given array, e.g. for [1, 2] the array
 * [[], [1], [1, 2]] is returned.
 *
 * @template T
 * @param {Iterable<T>} iterable
 * @returns {T[][]}
 */
export function sections(iterable) {
    const array = [...iterable];
    const sections = [];
    for (let i = 0; i < array.length + 1; i++) {
        sections.push(array.slice(0, i));
    }
    return sections;
}

/**
 * Returns an array containing all elements of the given
 * array but without duplicates.
 *
 * @template T
 * @param {Iterable<T>} iterable
 * @returns {T[]}
 */
export function unique(iterable) {
    return [...new Set(iterable)];
}

/**
 * @template T1, T2
 * @param {Iterable<T1>} iter1
 * @param {Iterable<T2>} iter2
 * @param {boolean} [fill=false]
 * @returns {[T1, T2][]}
 */
export function zip(iter1, iter2, fill = false) {
    const array1 = [...iter1];
    const array2 = [...iter2];
    /** @type {[T1, T2][]} */
    const result = [];
    const getLength = fill ? Math.max : Math.min;
    for (let i = 0; i < getLength(array1.length, array2.length); i++) {
        result.push([array1[i], array2[i]]);
    }
    return result;
}

/**
 * @template T1, T2, T
 * @param {Iterable<T1>} iter1
 * @param {Iterable<T2>} iter2
 * @param {(e1: T1, e2: T2) => T} mapFn
 * @returns {T[]}
 */
export function zipWith(iter1, iter2, mapFn) {
    return zip(iter1, iter2).map(([e1, e2]) => mapFn(e1, e2));
}
/**
 * Creates an sliding window over an array of a given width. Eg:
 * slidingWindow([1, 2, 3, 4], 2) => [[1, 2], [2, 3], [3, 4]]
 *
 * @template T
 * @param {T[]} arr the array over which to create a sliding window
 * @param {number} width the width of the window
 * @returns {T[][]} an array of tuples of size width
 */
export function slidingWindow(arr, width) {
    const res = [];
    for (let i = 0; i <= arr.length - width; i++) {
        res.push(arr.slice(i, i + width));
    }
    return res;
}

export function rotate(i, arr, inc = 1) {
    return (arr.length + i + inc) % arr.length;
}
