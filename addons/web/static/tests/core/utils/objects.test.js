import { describe, expect, test } from "@odoo/hoot";

import {
    deepCopy,
    deepEqual,
    isObject,
    omit,
    pick,
    shallowEqual,
    deepMerge,
} from "@web/core/utils/objects";

describe.current.tags("headless");

describe("shallowEqual", () => {
    test("simple valid cases", () => {
        expect(shallowEqual({}, {})).toBe(true);
        expect(shallowEqual({ a: 1 }, { a: 1 })).toBe(true);
        expect(shallowEqual({ a: 1, b: "x" }, { b: "x", a: 1 })).toBe(true);
    });

    test("simple invalid cases", () => {
        expect(shallowEqual({ a: 1 }, { a: 2 })).toBe(false);
        expect(shallowEqual({}, { a: 2 })).toBe(false);
        expect(shallowEqual({ a: 1 }, {})).toBe(false);
    });

    test("objects with non primitive values", () => {
        const obj = { x: "y" };
        expect(shallowEqual({ a: obj }, { a: obj })).toBe(true);
        expect(shallowEqual({ a: { x: "y" } }, { a: { x: "y" } })).toBe(false);

        const arr = ["x", "y", "z"];
        expect(shallowEqual({ a: arr }, { a: arr })).toBe(true);
        expect(shallowEqual({ a: ["x", "y", "z"] }, { a: ["x", "y", "z"] })).toBe(false);

        const fn = () => {};
        expect(shallowEqual({ a: fn }, { a: fn })).toBe(true);
        expect(shallowEqual({ a: () => {} }, { a: () => {} })).toBe(false);
    });

    test("custom comparison function", () => {
        const dateA = new Date();
        const dateB = new Date(dateA);

        expect(shallowEqual({ a: 1, date: dateA }, { a: 1, date: dateB })).toBe(false);
        expect(
            shallowEqual({ a: 1, date: dateA }, { a: 1, date: dateB }, (a, b) =>
                a instanceof Date ? Number(a) === Number(b) : a === b
            )
        ).toBe(true);
    });
});

test("deepEqual", () => {
    const obj1 = {
        a: ["a", "b", "c"],
        o: {
            b: true,
            n: 10,
        },
    };
    const obj2 = Object.assign({}, obj1);
    const obj3 = Object.assign({}, obj2, { some: "thing" });
    expect(deepEqual(obj1, obj2)).toBe(true);
    expect(deepEqual(obj1, obj3)).toBe(false);
    expect(deepEqual(obj2, obj3)).toBe(false);
});

test("deepCopy", () => {
    const obj = {
        a: ["a", "b", "c"],
        o: {
            b: true,
            n: 10,
        },
    };
    const copy = deepCopy(obj);
    expect(copy).not.toBe(obj);
    expect(copy).toEqual(obj);
    expect(copy.a).not.toBe(obj.a);
    expect(copy.o).not.toBe(obj.o);

    expect(deepCopy(new Date())).not.toBeInstanceOf(Date);
    expect(deepCopy(new Set(["a"]))).not.toBeInstanceOf(Set);
    expect(deepCopy(new Map([["a", 1]]))).not.toBeInstanceOf(Map);
});

test("isObject", () => {
    expect(isObject(null)).toBe(false);
    expect(isObject(undefined)).toBe(false);

    expect(isObject("a")).toBe(false);

    expect(isObject(true)).toBe(false);
    expect(isObject(false)).toBe(false);

    expect(isObject(10)).toBe(false);
    expect(isObject(10.01)).toBe(false);

    expect(isObject([])).toBe(true);
    expect(isObject([1, 2])).toBe(true);

    expect(isObject({})).toBe(true);
    expect(isObject({ a: 1 })).toBe(true);

    expect(isObject(() => {})).toBe(true);
    expect(isObject(new Set())).toBe(true);
    expect(isObject(new Map())).toBe(true);
    expect(isObject(new Date())).toBe(true);
});

test("omit", () => {
    expect(omit({})).toEqual({});
    expect(omit({}, "a")).toEqual({});
    expect(omit({ a: 1 })).toEqual({ a: 1 });
    expect(omit({ a: 1 }, "a")).toEqual({});
    expect(omit({ a: 1, b: 2 }, "c", "a")).toEqual({ b: 2 });
    expect(omit({ a: 1, b: 2 }, "b", "c")).toEqual({ a: 1 });
});

test("pick", () => {
    expect(pick({})).toEqual({});
    expect(pick({}, "a")).toEqual({});
    expect(pick({ a: 3, b: "a", c: [] }, "a")).toEqual({ a: 3 });
    expect(pick({ a: 3, b: "a", c: [] }, "a", "c")).toEqual({ a: 3, c: [] });
    expect(pick({ a: 3, b: "a", c: [] }, "a", "b", "c")).toEqual({ a: 3, b: "a", c: [] });

    // Non enumerable property
    class MyClass {
        get a() {
            return 1;
        }
    }
    const myClass = new MyClass();
    Object.defineProperty(myClass, "b", { enumerable: false, value: 2 });
    expect(pick(myClass, "a", "b")).toEqual({ a: 1, b: 2 });
});

test("deepMerge", () => {
    expect(
        deepMerge(
            {
                a: 1,
                b: {
                    b_a: 1,
                    b_b: 2,
                },
            },
            {
                a: 2,
                b: {
                    b_b: 3,
                    b_c: 4,
                },
            }
        )
    ).toEqual({
        a: 2,
        b: {
            b_a: 1,
            b_b: 3,
            b_c: 4,
        },
    });

    expect(deepMerge({}, {})).toEqual({});

    expect(deepMerge({ a: 1 }, {})).toEqual({ a: 1 });
    expect(deepMerge({}, { a: 1 })).toEqual({ a: 1 });
    expect(deepMerge({ a: 1 }, { b: 2 })).toEqual({ a: 1, b: 2 });
    expect(deepMerge({ a: 1 }, { a: 2 })).toEqual({ a: 2 });

    expect(deepMerge(undefined, { a: 1 })).toEqual({ a: 1 });
    expect(deepMerge({ a: 1 }, undefined)).toEqual({ a: 1 });
    expect(deepMerge(undefined, undefined)).toBe(undefined);
    expect(deepMerge({ a: undefined, b: undefined }, { a: { foo: "bar" } })).toEqual({
        a: { foo: "bar" },
        b: undefined,
    });

    expect(deepMerge("foo", 1)).toBe(undefined);
    expect(deepMerge(null, null)).toBe(undefined);

    const f = () => {};
    expect(deepMerge({ a: undefined }, { a: f })).toEqual({ a: f });

    // There's no current use for arrays, support can be added if needed
    expect(deepMerge({ a: [1, 2, 3] }, { a: [4] })).toEqual({ a: [4] });

    const symbolA = Symbol("A");
    const symbolB = Symbol("B");
    expect(
        deepMerge(
            {
                [symbolA]: 1,
            },
            {
                [symbolA]: 3,
                [symbolB]: 2,
            }
        )
    ).toEqual({
        [symbolA]: 3,
        [symbolB]: 2,
    });
});
