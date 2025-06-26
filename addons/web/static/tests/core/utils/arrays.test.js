import { describe, expect, test } from "@odoo/hoot";

import {
    cartesian,
    ensureArray,
    groupBy,
    intersection,
    shallowEqual,
    slidingWindow,
    sortBy,
    unique,
    zip,
    zipWith,
} from "@web/core/utils/arrays";

describe.current.tags("headless");

describe("groupby", () => {
    test("groupBy parameter validations", () => {
        // Safari: TypeError: undefined is not a function
        // Other navigator: array is not iterable
        expect(() => groupBy({})).toThrow(/TypeError: \w+ is not iterable/);
        expect(() => groupBy([], true)).toThrow(
            /Expected criterion of type 'string' or 'function' and got 'boolean'/
        );
        expect(() => groupBy([], 3)).toThrow(
            /Expected criterion of type 'string' or 'function' and got 'number'/
        );
        expect(() => groupBy([], {})).toThrow(
            /Expected criterion of type 'string' or 'function' and got 'object'/
        );
    });

    test("groupBy (no criterion)", () => {
        // criterion = default
        expect(groupBy(["a", "b", 1, true])).toEqual({
            1: [1],
            a: ["a"],
            b: ["b"],
            true: [true],
        });
    });

    test("groupBy by property", () => {
        expect(groupBy([{ x: "a" }, { x: "a" }, { x: "b" }], "x")).toEqual({
            a: [{ x: "a" }, { x: "a" }],
            b: [{ x: "b" }],
        });
    });

    test("groupBy", () => {
        expect(groupBy(["a", "b", 1, true], (x) => `el${x}`)).toEqual({
            ela: ["a"],
            elb: ["b"],
            el1: [1],
            eltrue: [true],
        });
    });
});

describe("sortby", () => {
    test("sortBy parameter validation", () => {
        expect(() => sortBy({})).toThrow(/TypeError: \w+ is not iterable/);
        expect(() => sortBy([Symbol("b"), Symbol("a")])).toThrow(
            /(Cannot convert a (Symbol value)|(symbol) to a number)|(can't convert symbol to number)/
        );
        expect(() => sortBy([2, 1, 5], true)).toThrow(
            /Expected criterion of type 'string' or 'function' and got 'boolean'/
        );
        expect(() => sortBy([2, 1, 5], 3)).toThrow(
            /Expected criterion of type 'string' or 'function' and got 'number'/
        );
        expect(() => sortBy([2, 1, 5], {})).toThrow(
            /Expected criterion of type 'string' or 'function' and got 'object'/
        );
    });

    test("sortBy do not sort in place", () => {
        const toSort = [2, 3, 1];
        sortBy(toSort);
        expect(toSort).toEqual([2, 3, 1]);
    });

    test("sortBy (no criterion)", () => {
        expect(sortBy([])).toEqual([]);
        expect(sortBy([2, 1, 5])).toEqual([1, 2, 5]);
        expect(sortBy([true, false, true])).toEqual([false, true, true]);
        expect(sortBy(["b", "a", "z"])).toEqual(["a", "b", "z"]);
        expect(sortBy([{ x: true }, { x: false }, { x: true }])).toEqual([
            { x: true },
            { x: false },
            { x: true },
        ]);
        expect(sortBy([{ x: 2 }, { x: 1 }, { x: 5 }])).toEqual([{ x: 2 }, { x: 1 }, { x: 5 }]);
        expect(sortBy([{ x: "b" }, { x: "a" }, { x: "z" }])).toEqual([
            { x: "b" },
            { x: "a" },
            { x: "z" },
        ]);
    });

    test("sortBy property", () => {
        expect(sortBy([], "x")).toEqual([]);
        expect(sortBy([2, 1, 5], "x")).toEqual([2, 1, 5]);
        expect(sortBy([true, false, true], "x")).toEqual([true, false, true]);
        expect(sortBy(["b", "a", "z"], "x")).toEqual(["b", "a", "z"]);
        expect(sortBy([{ x: true }, { x: false }, { x: true }], "x")).toEqual([
            { x: false },
            { x: true },
            { x: true },
        ]);
        expect(sortBy([{ x: 2 }, { x: 1 }, { x: 5 }], "x")).toEqual([{ x: 1 }, { x: 2 }, { x: 5 }]);
        expect(sortBy([{ x: "b" }, { x: "a" }, { x: "z" }], "x")).toEqual([
            { x: "a" },
            { x: "b" },
            { x: "z" },
        ]);
    });

    test("sortBy getter", () => {
        const getter = (obj) => obj.x;
        expect(sortBy([], getter)).toEqual([]);
        expect(sortBy([2, 1, 5], getter)).toEqual([2, 1, 5]);
        expect(sortBy([true, false, true], getter)).toEqual([true, false, true]);
        expect(sortBy(["b", "a", "z"], getter)).toEqual(["b", "a", "z"]);
        expect(sortBy([{ x: true }, { x: false }, { x: true }], getter)).toEqual([
            { x: false },
            { x: true },
            { x: true },
        ]);
        expect(sortBy([{ x: 2 }, { x: 1 }, { x: 5 }], getter)).toEqual([
            { x: 1 },
            { x: 2 },
            { x: 5 },
        ]);
        expect(sortBy([{ x: "b" }, { x: "a" }, { x: "z" }], getter)).toEqual([
            { x: "a" },
            { x: "b" },
            { x: "z" },
        ]);
    });

    test("sortBy descending order", () => {
        expect(sortBy([2, 1, 5], null, "desc")).toEqual([5, 2, 1]);
        expect(sortBy([{ x: "b" }, { x: "a" }, { x: "z" }], "x", "desc")).toEqual([
            { x: "z" },
            { x: "b" },
            { x: "a" },
        ]);
    });
});

describe("intersection", () => {
    test("intersection of arrays", () => {
        expect(intersection([], [1, 2])).toEqual([]);
        expect(intersection([1, 2], [])).toEqual([]);
        expect(intersection([1], [2])).toEqual([]);
        expect(intersection([1, 2], [2, 3])).toEqual([2]);
        expect(intersection([1, 2, 3], [1, 2, 3])).toEqual([1, 2, 3]);
    });
});

describe("cartesian", () => {
    test("cartesian product of zero arrays", () => {
        expect(cartesian()).toEqual([undefined], {
            message: "the unit of the product is a singleton",
        });
    });

    test("cartesian product of a single array", () => {
        expect(cartesian([])).toEqual([]);
        expect(cartesian([1])).toEqual([1], { message: "we don't want unecessary brackets" });
        expect(cartesian([1, 2])).toEqual([1, 2]);
        expect(cartesian([[1, 2]])).toEqual([[1, 2]], {
            message: "the internal structure of elements should be preserved",
        });
        expect(
            cartesian([
                [1, 2],
                [3, [2]],
            ])
        ).toEqual(
            [
                [1, 2],
                [3, [2]],
            ],
            { message: "the internal structure of elements should be preserved" }
        );
    });

    test("cartesian product of two arrays", () => {
        expect(cartesian([], [])).toEqual([]);
        expect(cartesian([1], [])).toEqual([]);
        expect(cartesian([1], [2])).toEqual([[1, 2]]);
        expect(cartesian([1, 2], [3])).toEqual([
            [1, 3],
            [2, 3],
        ]);
        expect(cartesian([[1], 4], [2, [3]])).toEqual(
            [
                [[1], 2],
                [[1], [3]],
                [4, 2],
                [4, [3]],
            ],
            { message: "the internal structure of elements should be preserved" }
        );
    });

    test("cartesian product of three arrays", () => {
        expect(cartesian([], [], [])).toEqual([]);
        expect(cartesian([1], [], [2, 5])).toEqual([]);
        expect(cartesian([1], [2], [3])).toEqual([[1, 2, 3]], {
            message: "we should have no unecessary brackets, we want elements to be 'triples'",
        });
        expect(cartesian([[1], 2], [3], [4])).toEqual(
            [
                [[1], 3, 4],
                [2, 3, 4],
            ],
            { message: "the internal structure of elements should be preserved" }
        );
    });

    test("cartesian product of four arrays", () => {
        expect(cartesian([1], [2], [3], [4])).toEqual([[1, 2, 3, 4]]);
    });
});

describe("ensureArray", () => {
    test("ensure array", () => {
        const arrayRef = [];
        expect(ensureArray(arrayRef)).not.toBe(arrayRef, {
            message: "Should be a different array",
        });
        expect(ensureArray([])).toEqual([]);
        expect(ensureArray()).toEqual([undefined]);
        expect(ensureArray(null)).toEqual([null]);
        expect(ensureArray({ a: 1 })).toEqual([{ a: 1 }]);
        expect(ensureArray("foo")).toEqual(["foo"]);
        expect(ensureArray([1, 2, "3"])).toEqual([1, 2, "3"]);
        expect(ensureArray(new Set([1, 2, 3]))).toEqual([1, 2, 3]);
    });
});

describe("unique", () => {
    test("unique array", () => {
        expect(unique([1, 2, 3, 2, 4, 3, 1, 4])).toEqual([1, 2, 3, 4]);
        expect(unique("a d c a b c d b".split(" "))).toEqual("a d c b".split(" "));
    });
});

describe("shallowEqual", () => {
    test("simple valid cases", () => {
        expect(shallowEqual([], [])).toBe(true);
        expect(shallowEqual([1], [1])).toBe(true);
        expect(shallowEqual([1, "a"], [1, "a"])).toBe(true);
    });

    test("simple invalid cases", () => {
        expect(shallowEqual([1], [])).not.toBe(true);
        expect(shallowEqual([], [1])).not.toBe(true);
        expect(shallowEqual([1, "b"], [1, "a"])).not.toBe(true);
    });

    test("arrays with non primitive values", () => {
        const obj = { b: 3 };
        expect(shallowEqual([obj], [obj])).toBe(true);
        expect(shallowEqual([{ b: 3 }], [{ b: 3 }])).not.toBe(true);

        const arr = ["x", "y", "z"];
        expect(shallowEqual([arr], [arr])).toBe(true);
        expect(shallowEqual([["x", "y", "z"]], [["x", "y", "z"]])).not.toBe(true);

        const fn = () => {};
        expect(shallowEqual([fn], [fn])).toBe(true);
        expect(shallowEqual([() => {}], [() => {}])).not.toBe(true);
    });
});

describe("zip", () => {
    test("zip", () => {
        expect(zip([1, 2], [])).toEqual([]);
        expect(zip([1, 2], ["a"])).toEqual([[1, "a"]]);
        expect(zip([1, 2], ["a", "b"])).toEqual([
            [1, "a"],
            [2, "b"],
        ]);
    });
});

describe("zipWith", () => {
    test("zipWith", () => {
        expect(zipWith([{ a: 1 }, { b: 2 }], ["a", "b"], (o, k) => o[k])).toEqual([1, 2]);
    });
});

describe("slidingWindow", () => {
    test("slidingWindow", () => {
        expect(slidingWindow([1, 2, 3, 4], 2)).toEqual([
            [1, 2],
            [2, 3],
            [3, 4],
        ]);
        expect(slidingWindow([1, 2, 3, 4], 4)).toEqual([[1, 2, 3, 4]]);
        expect(slidingWindow([1, 2, 3, 4], 5)).toEqual([]);
        expect(slidingWindow([], 1)).toEqual([]);
    });
});
