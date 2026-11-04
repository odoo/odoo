import { evalPartialContext, makeContext } from "@web/core/context";
import { expect, test, describe } from "@odoo/hoot";

describe.current.tags("headless");

describe("makeContext", () => {
    test("return empty context", () => {
        expect(makeContext([])).toEqual({});
    });

    test("duplicate a context", () => {
        const ctx1 = { a: 1 };
        const ctx2 = makeContext([ctx1]);
        expect(ctx1).not.toBe(ctx2);
        expect(ctx1).toEqual(ctx2);
    });

    test("can accept undefined or empty string", () => {
        expect(makeContext([undefined])).toEqual({});
        expect(makeContext([{ a: 1 }, undefined, { b: 2 }])).toEqual({ a: 1, b: 2 });
        expect(makeContext([""])).toEqual({});
        expect(makeContext([{ a: 1 }, "", { b: 2 }])).toEqual({ a: 1, b: 2 });
    });

    test("evaluate strings", () => {
        expect(makeContext(["{'a': 33}"])).toEqual({ a: 33 });
    });

    test("evaluated context is used as evaluation context along the way", () => {
        expect(makeContext([{ a: 1 }, "{'a': a + 1}"])).toEqual({ a: 2 });
        expect(makeContext([{ a: 1 }, "{'b': a + 1}"])).toEqual({ a: 1, b: 2 });
        expect(makeContext([{ a: 1 }, "{'b': a + 1}", "{'c': b + 1}"])).toEqual({
            a: 1,
            b: 2,
            c: 3,
        });
        expect(makeContext([{ a: 1 }, "{'b': a + 1}", "{'a': b + 1}"])).toEqual({ a: 3, b: 2 });
    });

    test("initial evaluation context", () => {
        expect(makeContext(["{'a': a + 1}"], { a: 1 })).toEqual({ a: 2 });
        expect(makeContext(["{'b': a + 1}"], { a: 1 })).toEqual({ b: 2 });
    });
});

describe("evalPartialContext", () => {
    test("static contexts", () => {
        expect(evalPartialContext("{}", {})).toEqual({});
        expect(evalPartialContext("{'a': 1}", {})).toEqual({ a: 1 });
        expect(evalPartialContext("{'a': 'b'}", {})).toEqual({ a: "b" });
        expect(evalPartialContext("{'a': true}", {})).toEqual({ a: true });
        expect(evalPartialContext("{'a': None}", {})).toEqual({ a: null });
    });

    test("complete dynamic contexts", () => {
        expect(evalPartialContext("{'a': a, 'b': 1}", { a: 2 })).toEqual({ a: 2, b: 1 });
    });

    test("partial dynamic contexts", () => {
        expect(evalPartialContext("{'a': a}", {})).toEqual({});
        expect(evalPartialContext("{'a': a, 'b': 1}", {})).toEqual({ b: 1 });
        expect(evalPartialContext("{'a': a, 'b': b}", { a: 2 })).toEqual({ a: 2 });
    });

    test("value of type obj (15)", () => {
        expect(evalPartialContext("{'a': a.b.c}", {})).toEqual({});
        expect(evalPartialContext("{'a': a.b.c}", { a: {} })).toEqual({});
        expect(evalPartialContext("{'a': a.b.c}", { a: { b: { c: 2 } } })).toEqual({ a: 2 });
    });

    test("value of type op (14)", () => {
        expect(evalPartialContext("{'a': a + 1}", {})).toEqual({});
        expect(evalPartialContext("{'a': a + b}", {})).toEqual({});
        expect(evalPartialContext("{'a': a + b}", { a: 2 })).toEqual({});
        expect(evalPartialContext("{'a': a + 1}", { a: 2 })).toEqual({ a: 3 });
        expect(evalPartialContext("{'a': a + b}", { a: 2, b: 3 })).toEqual({ a: 5 });
    });
});
