odoo.define('web.util_tests', function (require) {
"use strict";

var utils = require('web.utils');

QUnit.module('core', {}, function () {

    QUnit.module('utils');

    QUnit.test('findWhere', function (assert) {
        assert.expect(7);

        const { findWhere } = utils;

        const list = [
            undefined,
            { a: 1, b: 2 },
            { a: 2, b: 2 },
            { a: 1, b: 3 },
            { a: 1, b: 4 },
            { a: 2, b: 4 },
        ];

        assert.deepEqual(findWhere(list, { a: 1 }), { a: 1, b: 2 });
        assert.deepEqual(findWhere(list, { a: 2 }), { a: 2, b: 2 });
        assert.deepEqual(findWhere(list, { b: 4 }), { a: 1, b: 4 });
        assert.deepEqual(findWhere(list, { b: 4, a: 2 }), { a: 2, b: 4 });
        assert.ok(findWhere([], { a: 1 }) === undefined);
        assert.ok(findWhere(list, { a: 1, b: 5 }) === undefined);
        assert.ok(findWhere(list, { c: 1 }) === undefined);
    });

    QUnit.test('groupBy', function (assert) {
        assert.expect(7);

        const { groupBy } = utils;

        // Invalid
        assert.throws(
            () => groupBy({}),
            new TypeError(`list is not iterable`)
        );
        assert.throws(
            () => groupBy([], true),
            new Error(`Expected criterion of type 'string' or 'function' and got 'boolean'`)
        );
        assert.throws(
            () => groupBy([], 3),
            new Error(`Expected criterion of type 'string' or 'function' and got 'number'`)
        );
        assert.throws(
            () => groupBy([], {}),
            new Error(`Expected criterion of type 'string' or 'function' and got 'object'`)
        );

        // criterion = default
        assert.deepEqual(
            groupBy(["a", "b", 1, true]),
            {
                1: [1],
                a: ["a"],
                b: ["b"],
                true: [true],
            }
        );
        // criterion = string
        assert.deepEqual(
            groupBy([{ x: "a" }, { x: "a" }, { x: "b" }], "x"),
            {
                a: [{ x: "a" }, { x: "a" }],
                b: [{ x: "b" }],
            }
        );
        // criterion = function
        assert.deepEqual(
            groupBy(["a", "b", 1, true], (x) => `el${x}`),
            {
                ela: ["a"],
                elb: ["b"],
                el1: [1],
                eltrue: [true],
            }
        );
    });

    QUnit.test('intersperse', function (assert) {
        assert.expect(27);

        var intersperse = utils.intersperse;

        assert.strictEqual(intersperse("", []), "");
        assert.strictEqual(intersperse("0", []), "0");
        assert.strictEqual(intersperse("012", []), "012");
        assert.strictEqual(intersperse("1", []), "1");
        assert.strictEqual(intersperse("12", []), "12");
        assert.strictEqual(intersperse("123", []), "123");
        assert.strictEqual(intersperse("1234", []), "1234");
        assert.strictEqual(intersperse("123456789", []), "123456789");
        assert.strictEqual(intersperse("&ab%#@1", []), "&ab%#@1");

        assert.strictEqual(intersperse("0", []), "0");
        assert.strictEqual(intersperse("0", [1]), "0");
        assert.strictEqual(intersperse("0", [2]), "0");
        assert.strictEqual(intersperse("0", [200]), "0");

        assert.strictEqual(intersperse("12345678", [0], '.'), '12345678');
        assert.strictEqual(intersperse("", [1], '.'), '');
        assert.strictEqual(intersperse("12345678", [1], '.'), '1234567.8');
        assert.strictEqual(intersperse("12345678", [1], '.'), '1234567.8');
        assert.strictEqual(intersperse("12345678", [2], '.'), '123456.78');
        assert.strictEqual(intersperse("12345678", [2, 1], '.'), '12345.6.78');
        assert.strictEqual(intersperse("12345678", [2, 0], '.'), '12.34.56.78');
        assert.strictEqual(intersperse("12345678", [-1, 2], '.'), '12345678');
        assert.strictEqual(intersperse("12345678", [2, -1], '.'), '123456.78');
        assert.strictEqual(intersperse("12345678", [2, 0, 1], '.'), '12.34.56.78');
        assert.strictEqual(intersperse("12345678", [2, 0, 0], '.'), '12.34.56.78');
        assert.strictEqual(intersperse("12345678", [2, 0, -1], '.'), '12.34.56.78');
        assert.strictEqual(intersperse("12345678", [3,3,3,3], '.'), '12.345.678');
        assert.strictEqual(intersperse("12345678", [3,0], '.'), '12.345.678');
    });

    QUnit.test('is_bin_size', function (assert) {
        assert.expect(3);

        var is_bin_size = utils.is_bin_size;

        assert.strictEqual(is_bin_size('Cg=='), false);
        assert.strictEqual(is_bin_size('2.5 Mb'), true);
        // should also work for non-latin languages (e.g. russian)
        assert.strictEqual(is_bin_size('64.2 Кб'), true);
    });

    QUnit.test('unaccent', function (assert) {
        assert.expect(3);

        var singleCharacters = utils.unaccent("ⱮɀꝾƶⱵȥ");
        var doubledCharacters = utils.unaccent("ǱǄꝎꜩꝡƕ");
        var caseSensetiveCharacters = utils.unaccent("ⱮɀꝾƶⱵȥ", true);

        assert.strictEqual("mzgzhz", singleCharacters);
        assert.strictEqual("dzdzootzvyhv", doubledCharacters);
        assert.strictEqual("MzGzHz", caseSensetiveCharacters);
    });

    QUnit.test('human_number', function (assert) {
        assert.expect(26);

        var human_number = utils.human_number;

        assert.strictEqual(human_number(1020, 2, 1), '1.02k');
        assert.strictEqual(human_number(1020000, 2, 2), '1020k');
        assert.strictEqual(human_number(10200000, 2, 2), '10.2M');
        assert.strictEqual(human_number(1020, 2, 1), '1.02k');
        assert.strictEqual(human_number(1002, 2, 1), '1k');
        assert.strictEqual(human_number(101, 2, 1), '101');
        assert.strictEqual(human_number(64.2, 2, 1), '64');
        assert.strictEqual(human_number(1e+18), '1E');
        assert.strictEqual(human_number(1e+21, 2, 1), '1e+21');
        assert.strictEqual(human_number(1.0045e+22, 2, 1), '1e+22');
        assert.strictEqual(human_number(1.0045e+22, 3, 1), '1.005e+22');
        assert.strictEqual(human_number(1.012e+43, 2, 1), '1.01e+43');
        assert.strictEqual(human_number(1.012e+43, 2, 2), '1.01e+43');

        assert.strictEqual(human_number(-1020, 2, 1), '-1.02k');
        assert.strictEqual(human_number(-1020000, 2, 2), '-1020k');
        assert.strictEqual(human_number(-10200000, 2, 2), '-10.2M');
        assert.strictEqual(human_number(-1020, 2, 1), '-1.02k');
        assert.strictEqual(human_number(-1002, 2, 1), '-1k');
        assert.strictEqual(human_number(-101, 2, 1), '-101');
        assert.strictEqual(human_number(-64.2, 2, 1), '-64');
        assert.strictEqual(human_number(-1e+18), '-1E');
        assert.strictEqual(human_number(-1e+21, 2, 1), '-1e+21');
        assert.strictEqual(human_number(-1.0045e+22, 2, 1), '-1e+22');
        assert.strictEqual(human_number(-1.0045e+22, 3, 1), '-1.004e+22');
        assert.strictEqual(human_number(-1.012e+43, 2, 1), '-1.01e+43');
        assert.strictEqual(human_number(-1.012e+43, 2, 2), '-1.01e+43');
    });

    QUnit.test('patch a class', function(assert) {
        assert.expect(4);

        class Parent {
            foo() {
                return 'Parent foo';
            }
        }

        class Child extends Parent {
            bar() {
                return 'Child bar';
            }
        }

        const removePatch = utils.patch(Child, 'patch', {
            foo() {
                return this._super() + ' patch foo';
            },
            bar() {
                return this._super() + ' patch bar';
            }
        })

        const child = new Child();

        assert.strictEqual(child.foo(), 'Parent foo patch foo')
        assert.strictEqual(child.bar(), 'Child bar patch bar')

        removePatch();

        assert.strictEqual(child.foo(), 'Parent foo');
        assert.strictEqual(child.bar(), 'Child bar');
    })

    QUnit.test('round_decimals', function (assert) {
        assert.expect(21);

        var round_di = utils.round_decimals;

        assert.strictEqual(String(round_di(1.0, 0)), '1');
        assert.strictEqual(String(round_di(1.0, 1)), '1');
        assert.strictEqual(String(round_di(1.0, 2)), '1');
        assert.strictEqual(String(round_di(1.0, 3)), '1');
        assert.strictEqual(String(round_di(1.0, 4)), '1');
        assert.strictEqual(String(round_di(1.0, 5)), '1');
        assert.strictEqual(String(round_di(1.0, 6)), '1');
        assert.strictEqual(String(round_di(1.0, 7)), '1');
        assert.strictEqual(String(round_di(1.0, 8)), '1');
        assert.strictEqual(String(round_di(0.5, 0)), '1');
        assert.strictEqual(String(round_di(-0.5, 0)), '-1');
        assert.strictEqual(String(round_di(2.6745, 3)), '2.6750000000000003');
        assert.strictEqual(String(round_di(-2.6745, 3)), '-2.6750000000000003');
        assert.strictEqual(String(round_di(2.6744, 3)), '2.674');
        assert.strictEqual(String(round_di(-2.6744, 3)), '-2.674');
        assert.strictEqual(String(round_di(0.0004, 3)), '0');
        assert.strictEqual(String(round_di(-0.0004, 3)), '0');
        assert.strictEqual(String(round_di(357.4555, 3)), '357.456');
        assert.strictEqual(String(round_di(-357.4555, 3)), '-357.456');
        assert.strictEqual(String(round_di(457.4554, 3)), '457.455');
        assert.strictEqual(String(round_di(-457.4554, 3)), '-457.455');
    });

    QUnit.test('round_precision', function (assert) {
        assert.expect(26);

        var round_pr = utils.round_precision;

        assert.strictEqual(String(round_pr(1.0, 1)), '1');
        assert.strictEqual(String(round_pr(1.0, 0.1)), '1');
        assert.strictEqual(String(round_pr(1.0, 0.01)), '1');
        assert.strictEqual(String(round_pr(1.0, 0.001)), '1');
        assert.strictEqual(String(round_pr(1.0, 0.0001)), '1');
        assert.strictEqual(String(round_pr(1.0, 0.00001)), '1');
        assert.strictEqual(String(round_pr(1.0, 0.000001)), '1');
        assert.strictEqual(String(round_pr(1.0, 0.0000001)), '1');
        assert.strictEqual(String(round_pr(1.0, 0.00000001)), '1');
        assert.strictEqual(String(round_pr(0.5, 1)), '1');
        assert.strictEqual(String(round_pr(-0.5, 1)), '-1');
        assert.strictEqual(String(round_pr(2.6745, 0.001)), '2.6750000000000003');
        assert.strictEqual(String(round_pr(-2.6745, 0.001)), '-2.6750000000000003');
        assert.strictEqual(String(round_pr(2.6744, 0.001)), '2.674');
        assert.strictEqual(String(round_pr(-2.6744, 0.001)), '-2.674');
        assert.strictEqual(String(round_pr(0.0004, 0.001)), '0');
        assert.strictEqual(String(round_pr(-0.0004, 0.001)), '0');
        assert.strictEqual(String(round_pr(357.4555, 0.001)), '357.456');
        assert.strictEqual(String(round_pr(-357.4555, 0.001)), '-357.456');
        assert.strictEqual(String(round_pr(457.4554, 0.001)), '457.455');
        assert.strictEqual(String(round_pr(-457.4554, 0.001)), '-457.455');
        assert.strictEqual(String(round_pr(-457.4554, 0.05)), '-457.45000000000005');
        assert.strictEqual(String(round_pr(457.444, 0.5)), '457.5');
        assert.strictEqual(String(round_pr(457.3, 5)), '455');
        assert.strictEqual(String(round_pr(457.5, 5)), '460');
        assert.strictEqual(String(round_pr(457.1, 3)), '456');
    });

    QUnit.test('sortBy', function (assert) {
        assert.expect(27);
        const { sortBy } = utils;
        const bools = [true, false, true];
        const ints = [2, 1, 5];
        const strs = ['b', 'a', 'z'];
        const objbools = [{ x: true }, { x: false }, { x: true }];
        const objints = [{ x: 2 }, { x: 1 }, { x: 5 }];
        const objstrss = [{ x: 'b' }, { x: 'a' }, { x: 'z' }];

        // Invalid
        assert.throws(
            () => sortBy({}),
            new TypeError(`array.slice is not a function`)
        );
        assert.throws(
            () => sortBy([Symbol('b'), Symbol('a')]),
            new TypeError(`Cannot convert a Symbol value to a number`)
        );
        assert.throws(
            () => sortBy(ints, true),
            new Error(`Expected criterion of type 'string' or 'function' and got 'boolean'`)
        );
        assert.throws(
            () => sortBy(ints, 3),
            new Error(`Expected criterion of type 'string' or 'function' and got 'number'`)
        );
        assert.throws(
            () => sortBy(ints, {}),
            new Error(`Expected criterion of type 'string' or 'function' and got 'object'`)
        );
        // Do not sort in place
        const toSort = [2, 3, 1];
        sortBy(toSort);
        assert.deepEqual(toSort, [2, 3, 1]);
        // Sort (no criterion)
        assert.deepEqual(sortBy([]), []);
        assert.deepEqual(sortBy(ints), [1, 2, 5]);
        assert.deepEqual(sortBy(bools), [false, true, true]);
        assert.deepEqual(sortBy(strs), ['a', 'b', 'z']);
        assert.deepEqual(sortBy(objbools), [{ x: true }, { x: false }, { x: true }]);
        assert.deepEqual(sortBy(objints), [{ x: 2 }, { x: 1 }, { x: 5 }]);
        assert.deepEqual(sortBy(objstrss), [{ x: 'b' }, { x: 'a' }, { x: 'z' }]);
        // Sort by property
        const prop = 'x';
        assert.deepEqual(sortBy([], prop), []);
        assert.deepEqual(sortBy(ints, prop), [2, 1, 5]);
        assert.deepEqual(sortBy(bools, prop), [true, false, true]);
        assert.deepEqual(sortBy(strs, prop), ['b', 'a', 'z']);
        assert.deepEqual(sortBy(objbools, prop), [{ x: false }, { x: true }, { x: true }]);
        assert.deepEqual(sortBy(objints, prop), [{ x: 1 }, { x: 2 }, { x: 5 }]);
        assert.deepEqual(sortBy(objstrss, prop), [{ x: 'a' }, { x: 'b' }, { x: 'z' }]);
        // Sort by getter
        const getter = obj => obj.x;
        assert.deepEqual(sortBy([], getter), []);
        assert.deepEqual(sortBy(ints, getter), [2, 1, 5]);
        assert.deepEqual(sortBy(bools, getter), [true, false, true]);
        assert.deepEqual(sortBy(strs, getter), ['b', 'a', 'z']);
        assert.deepEqual(sortBy(objbools, getter), [{ x: false }, { x: true }, { x: true }]);
        assert.deepEqual(sortBy(objints, getter), [{ x: 1 }, { x: 2 }, { x: 5 }]);
        assert.deepEqual(sortBy(objstrss, getter), [{ x: 'a' }, { x: 'b' }, { x: 'z' }]);
    });
});

});
