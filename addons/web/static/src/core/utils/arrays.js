/** @odoo-module **/

/**
 * Same values returned as those returned by cartesian function for case n = 0
 * and n > 1. For n = 1, brackets are put around the unique parameter elements.
 *
 * @returns {Array}
 */
function _cartesian() {
    const args = Array.prototype.slice.call(arguments);
    if (args.length === 0) {
        return [undefined];
    }
    const firstArray = args[0].map(function (elem) {
        return [elem];
    });
    if (args.length === 1) {
        return firstArray;
    }
    const productOfOtherArrays = _cartesian.apply(null, args.slice(1));
    return firstArray.reduce(function (acc, elem) {
        return acc.concat(
            productOfOtherArrays.map(function (tuple) {
                return elem.concat(tuple);
            })
        );
    }, []);
}

/**
 * Helper function returning an extraction handler to use on array elements to
 * return a certain attribute or mutated form of the element.
 *
 * @private
 * @param {string | function} [criterion]
 * @returns {(element: any) => any}
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
 * Returns the array of elements contained in both arrays.
 *
 * @param {any[]} array1
 * @param {any[]} array2
 * @returns {any[]}
 */
export function intersection(array1, array2) {
    return array1.filter((v) => array2.includes(v));
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
 * @param {any[]} array
 * @param {string | function} [criterion]
 * @returns {Object}
 */
export function groupBy(array, criterion) {
    const extract = _getExtractorFrom(criterion);
    const groups = {};
    for (const element of array) {
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
 * @param {any[]} array
 * @param {string | function} [criterion]
 * @param {"asc" | "desc"} [order="asc"]
 * @returns {any[]}
 */
export function sortBy(array, criterion, order = "asc") {
    const extract = _getExtractorFrom(criterion);
    return array.slice().sort((elA, elB) => {
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
 * @param {any[]} arrayA
 * @param {any[]} arrayB
 * @returns an array containing all the elements of arrayA
 * that are not in arrayB and vice-versa.
 */
export function symmetricalDifference(arrayA, arrayB) {
    return arrayA
        .filter((id) => !arrayB.includes(id))
        .concat(arrayB.filter((id) => !arrayA.includes(id)));
}

/**
 * Returns the product of any number n of arrays.
 * The internal structures of their elements is preserved.
 * For n = 1, no brackets are put around the unique parameter elements
 * For n = 0, [undefined] is returned since it is the unit
 * of the cartesian product (up to isomorphism).
 *
 * @returns {Array}
 */
export function cartesian() {
    const args = Array.prototype.slice.call(arguments);
    if (args.length === 0) {
        return [undefined];
    } else if (args.length === 1) {
        return args[0];
    } else {
        return _cartesian.apply(null, args);
    }
}

/**
 * Shallow compares two arrays.
 * @param {any[]} arrayA
 * @param {any[]} arrayB
 * @returns {boolean} true iff arrayA and arrayB are shallow equal
 */
export function shallowEqual(arrayA, arrayB) {
    if (arrayA.length !== arrayB.length) {
        return false;
    }
    for (let i = 0; i < arrayA.length; i++) {
        if (arrayA[i] !== arrayB[i]) {
            return false;
        }
    }
    return true;
}

/**
 * Returns all initial sections of a given array, e.g. for [1, 2] the array
 * [[], [1], [1, 2]] is returned.
 *
 * @param {Array} array
 * @returns {Array[]}
 */
export function sections(array) {
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
 * @param {T[]} array
 * @returns {T[]}
 */
export function unique(array) {
    return Array.from(new Set(array));
}
