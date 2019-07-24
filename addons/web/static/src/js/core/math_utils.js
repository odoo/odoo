odoo.define('web.mathUtils', function () {
"use strict";

/**
 * Same values returned as those returned by cartesian function for case n = 0
 * and n > 1. For n = 1, brackets are put around the unique parameter elements.
 *
 * @returns {Array}
 */
function _cartesian() {
    var args = Array.prototype.slice.call(arguments);
    if (args.length === 0) {
        return [undefined];
    }
    var firstArray = args[0].map(function (elem) {
        return [elem];
    });
    if (args.length === 1) {
        return firstArray;
    }
    var productOfOtherArrays = _cartesian.apply(null, args.slice(1));
    var result = firstArray.reduce(
        function (acc, elem) {
            return acc.concat(productOfOtherArrays.map(function (tuple) {
                return elem.concat(tuple);
            }));
        },
        []
    );
    return result;
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
function cartesian() {
    var args = Array.prototype.slice.call(arguments);
    if (args.length === 0) {
        return [undefined];
    } else if (args.length === 1) {
        return args[0];
    } else {
        return _cartesian.apply(null, args);
    }
}

/**
 * Returns all initial sections of a given array, e.g. for [1, 2] the array
 * [[], [1], [1, 2]] is returned.
 *
 * @param {Array} array
 * @returns {Array[]}
 */
function sections(array) {
    var sections = [];
    for (var i = 0; i < array.length + 1; i++) {
        sections.push(array.slice(0, i));
    }
    return sections;
}

return {
    cartesian: cartesian,
    sections: sections,
};

});
