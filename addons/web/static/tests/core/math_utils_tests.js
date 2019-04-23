odoo.define('web.math_utils_tests', function(require) {
"use strict";

var mathUtils = require('web.mathUtils');
var cartesian = mathUtils.cartesian;

QUnit.module('mathUtils', function () {

    QUnit.module('cartesian');


    QUnit.test('cartesian product of zero arrays', function(assert) {
        assert.expect(1);
        assert.deepEqual(cartesian(), [undefined],
            "the unit of the product is a singleton");
    });

    QUnit.test('cartesian product of a single array', function(assert) {
        assert.expect(5);
        assert.deepEqual(cartesian([]), []);
        assert.deepEqual(cartesian([1]), [1],
            "we don't want unecessary brackets");
        assert.deepEqual(cartesian([1, 2]), [1, 2]);
        assert.deepEqual(cartesian([[1, 2]]), [[1, 2]],
            "the internal structure of elements should be preserved");
        assert.deepEqual(cartesian([[1, 2], [3, [2]]]), [[1, 2], [3, [2]]],
            "the internal structure of elements should be preserved");
    });

    QUnit.test('cartesian product of two arrays', function(assert) {
        assert.expect(5);
        assert.deepEqual(cartesian([], []), []);
        assert.deepEqual(cartesian([1], []), []);
        assert.deepEqual(cartesian([1], [2]), [[1, 2]]);
        assert.deepEqual(cartesian([1, 2], [3]), [[1, 3], [2, 3]]);
        assert.deepEqual(cartesian([[1], 4], [2, [3]]), [[[1], 2], [[1], [3]], [4, 2], [4, [3]] ],
            "the internal structure of elements should be preserved");
    });

    QUnit.test('cartesian product of three arrays', function(assert) {
        assert.expect(4);
        assert.deepEqual(cartesian([], [], []), []);
        assert.deepEqual(cartesian([1], [], [2, 5]), []);
        assert.deepEqual(cartesian([1], [2], [3]), [[1, 2, 3]],
            "we should have no unecessary brackets, we want elements to be 'triples'");
        assert.deepEqual(cartesian([[1], 2], [3], [4]), [[[1], 3, 4], [2, 3, 4]],
            "the internal structure of elements should be preserved");
    });

    QUnit.test('cartesian product of four arrays', function(assert) {
        assert.expect(1);
        assert.deepEqual(cartesian([1], [2], [3], [4]), [[1, 2, 3, 4]]);
    });

});
});