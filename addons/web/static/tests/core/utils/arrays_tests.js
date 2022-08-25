/** @odoo-module **/

import {
    cartesian,
    groupBy,
    intersection,
    shallowEqual,
    sortBy,
    unique,
} from "@web/core/utils/arrays";

QUnit.module("utils", () => {
    QUnit.module("Arrays");

    QUnit.test("groupBy parameter validations", function (assert) {
        // Safari: TypeError: undefined is not a function
        // Other navigator: array is not iterable
        assert.throws(
            () => groupBy({}),
            /array is not iterable|TypeError: undefined is not a function/
        );
        assert.throws(
            () => groupBy([], true),
            /Expected criterion of type 'string' or 'function' and got 'boolean'/
        );
        assert.throws(
            () => groupBy([], 3),
            /Expected criterion of type 'string' or 'function' and got 'number'/
        );
        assert.throws(
            () => groupBy([], {}),
            /Expected criterion of type 'string' or 'function' and got 'object'/
        );
    });

    QUnit.test("groupBy (no criterion)", function (assert) {
        // criterion = default
        assert.deepEqual(groupBy(["a", "b", 1, true]), {
            1: [1],
            a: ["a"],
            b: ["b"],
            true: [true],
        });
    });

    QUnit.test("groupBy by property", function (assert) {
        assert.deepEqual(groupBy([{ x: "a" }, { x: "a" }, { x: "b" }], "x"), {
            a: [{ x: "a" }, { x: "a" }],
            b: [{ x: "b" }],
        });
    });

    QUnit.test("groupBy", function (assert) {
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

    QUnit.test("sortBy parameter validation", function (assert) {
        assert.throws(() => sortBy({}), /array.slice is not a function/);
        assert.throws(
            () => sortBy([Symbol("b"), Symbol("a")]),
            /(Cannot convert a (Symbol value)|(symbol) to a number)|(can't convert symbol to number)/
        );
        assert.throws(
            () => sortBy([2, 1, 5], true),
            /Expected criterion of type 'string' or 'function' and got 'boolean'/
        );
        assert.throws(
            () => sortBy([2, 1, 5], 3),
            /Expected criterion of type 'string' or 'function' and got 'number'/
        );
        assert.throws(
            () => sortBy([2, 1, 5], {}),
            /Expected criterion of type 'string' or 'function' and got 'object'/
        );
    });

    QUnit.test("sortBy do not sort in place", function (assert) {
        const toSort = [2, 3, 1];
        sortBy(toSort);
        assert.deepEqual(toSort, [2, 3, 1]);
    });

    QUnit.test("sortBy (no criterion)", function (assert) {
        assert.deepEqual(sortBy([]), []);
        assert.deepEqual(sortBy([2, 1, 5]), [1, 2, 5]);
        assert.deepEqual(sortBy([true, false, true]), [false, true, true]);
        assert.deepEqual(sortBy(["b", "a", "z"]), ["a", "b", "z"]);
        assert.deepEqual(sortBy([{ x: true }, { x: false }, { x: true }]), [
            { x: true },
            { x: false },
            { x: true },
        ]);
        assert.deepEqual(sortBy([{ x: 2 }, { x: 1 }, { x: 5 }]), [{ x: 2 }, { x: 1 }, { x: 5 }]);
        assert.deepEqual(sortBy([{ x: "b" }, { x: "a" }, { x: "z" }]), [
            { x: "b" },
            { x: "a" },
            { x: "z" },
        ]);
    });

    QUnit.test("sortBy property", function (assert) {
        assert.deepEqual(sortBy([], "x"), []);
        assert.deepEqual(sortBy([2, 1, 5], "x"), [2, 1, 5]);
        assert.deepEqual(sortBy([true, false, true], "x"), [true, false, true]);
        assert.deepEqual(sortBy(["b", "a", "z"], "x"), ["b", "a", "z"]);
        assert.deepEqual(sortBy([{ x: true }, { x: false }, { x: true }], "x"), [
            { x: false },
            { x: true },
            { x: true },
        ]);
        assert.deepEqual(sortBy([{ x: 2 }, { x: 1 }, { x: 5 }], "x"), [
            { x: 1 },
            { x: 2 },
            { x: 5 },
        ]);
        assert.deepEqual(sortBy([{ x: "b" }, { x: "a" }, { x: "z" }], "x"), [
            { x: "a" },
            { x: "b" },
            { x: "z" },
        ]);
    });

    QUnit.test("sortBy getter", function (assert) {
        const getter = (obj) => obj.x;
        assert.deepEqual(sortBy([], getter), []);
        assert.deepEqual(sortBy([2, 1, 5], getter), [2, 1, 5]);
        assert.deepEqual(sortBy([true, false, true], getter), [true, false, true]);
        assert.deepEqual(sortBy(["b", "a", "z"], getter), ["b", "a", "z"]);
        assert.deepEqual(sortBy([{ x: true }, { x: false }, { x: true }], getter), [
            { x: false },
            { x: true },
            { x: true },
        ]);
        assert.deepEqual(sortBy([{ x: 2 }, { x: 1 }, { x: 5 }], getter), [
            { x: 1 },
            { x: 2 },
            { x: 5 },
        ]);
        assert.deepEqual(sortBy([{ x: "b" }, { x: "a" }, { x: "z" }], getter), [
            { x: "a" },
            { x: "b" },
            { x: "z" },
        ]);
    });

    QUnit.test("sortBy descending order", function (assert) {
        assert.deepEqual(sortBy([2, 1, 5], null, "desc"), [5, 2, 1]);
        assert.deepEqual(sortBy([{ x: "b" }, { x: "a" }, { x: "z" }], "x", "desc"), [
            { x: "z" },
            { x: "b" },
            { x: "a" },
        ]);
    });

    QUnit.test("intersection of arrays", function (assert) {
        assert.deepEqual(intersection([], [1, 2]), []);
        assert.deepEqual(intersection([1, 2], []), []);
        assert.deepEqual(intersection([1], [2]), []);
        assert.deepEqual(intersection([1, 2], [2, 3]), [2]);
        assert.deepEqual(intersection([1, 2, 3], [1, 2, 3]), [1, 2, 3]);
    });

    QUnit.test("cartesian product of zero arrays", function (assert) {
        assert.deepEqual(cartesian(), [undefined], "the unit of the product is a singleton");
    });

    QUnit.test("cartesian product of a single array", function (assert) {
        assert.deepEqual(cartesian([]), []);
        assert.deepEqual(cartesian([1]), [1], "we don't want unecessary brackets");
        assert.deepEqual(cartesian([1, 2]), [1, 2]);
        assert.deepEqual(
            cartesian([[1, 2]]),
            [[1, 2]],
            "the internal structure of elements should be preserved"
        );
        assert.deepEqual(
            cartesian([
                [1, 2],
                [3, [2]],
            ]),
            [
                [1, 2],
                [3, [2]],
            ],
            "the internal structure of elements should be preserved"
        );
    });

    QUnit.test("cartesian product of two arrays", function (assert) {
        assert.deepEqual(cartesian([], []), []);
        assert.deepEqual(cartesian([1], []), []);
        assert.deepEqual(cartesian([1], [2]), [[1, 2]]);
        assert.deepEqual(cartesian([1, 2], [3]), [
            [1, 3],
            [2, 3],
        ]);
        assert.deepEqual(
            cartesian([[1], 4], [2, [3]]),
            [
                [[1], 2],
                [[1], [3]],
                [4, 2],
                [4, [3]],
            ],
            "the internal structure of elements should be preserved"
        );
    });

    QUnit.test("cartesian product of three arrays", function (assert) {
        assert.deepEqual(cartesian([], [], []), []);
        assert.deepEqual(cartesian([1], [], [2, 5]), []);
        assert.deepEqual(
            cartesian([1], [2], [3]),
            [[1, 2, 3]],
            "we should have no unecessary brackets, we want elements to be 'triples'"
        );
        assert.deepEqual(
            cartesian([[1], 2], [3], [4]),
            [
                [[1], 3, 4],
                [2, 3, 4],
            ],
            "the internal structure of elements should be preserved"
        );
    });

    QUnit.test("cartesian product of four arrays", function (assert) {
        assert.deepEqual(cartesian([1], [2], [3], [4]), [[1, 2, 3, 4]]);
    });

    QUnit.test("unique array", function (assert) {
        assert.deepEqual(unique([1, 2, 3, 2, 4, 3, 1, 4]), [1, 2, 3, 4]);
        assert.deepEqual(unique("a d c a b c d b".split(" ")), "a d c b".split(" "));
    });

    QUnit.test("shallowEqual: simple valid cases", function (assert) {
        assert.ok(shallowEqual([], []));
        assert.ok(shallowEqual([1], [1]));
        assert.ok(shallowEqual([1, "a"], [1, "a"]));
    });

    QUnit.test("shallowEqual: simple invalid cases", function (assert) {
        assert.notOk(shallowEqual([1], []));
        assert.notOk(shallowEqual([], [1]));
        assert.notOk(shallowEqual([1, "b"], [1, "a"]));
    });

    QUnit.test("shallowEqual: arrays with non primitive values", function (assert) {
        const obj = { b: 3 };
        assert.ok(shallowEqual([obj], [obj]));
        assert.notOk(shallowEqual([{ b: 3 }], [{ b: 3 }]));

        const arr = ["x", "y", "z"];
        assert.ok(shallowEqual([arr], [arr]));
        assert.notOk(shallowEqual([["x", "y", "z"]], [["x", "y", "z"]]));

        const fn = () => {};
        assert.ok(shallowEqual([fn], [fn]));
        assert.notOk(shallowEqual([() => {}], [() => {}]));
    });
});
