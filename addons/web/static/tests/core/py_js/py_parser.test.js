import { describe, expect, test } from "@odoo/hoot";

import { parseExpr } from "@web/core/py_js/py";

describe.current.tags("headless");

test("can parse basic elements", () => {
    expect(parseExpr("1")).toEqual({ type: 0 /* Number */, value: 1 });
    expect(parseExpr('"foo"')).toEqual({ type: 1 /* String */, value: "foo" });
    expect(parseExpr("foo")).toEqual({ type: 5 /* Name */, value: "foo" });
    expect(parseExpr("True")).toEqual({ type: 2 /* Boolean */, value: true });
    expect(parseExpr("False")).toEqual({ type: 2 /* Boolean */, value: false });
    expect(parseExpr("None")).toEqual({ type: 3 /* None */ });
});

test("cannot parse empty string", () => {
    expect(() => parseExpr("")).toThrow(/Error: Missing token/);
});

test("can parse unary operator -", () => {
    expect(parseExpr("-1")).toEqual({
        type: 6 /* UnaryOperator */,
        op: "-",
        right: { type: 0 /* Number */, value: 1 },
    });
    expect(parseExpr("-foo")).toEqual({
        type: 6 /* UnaryOperator */,
        op: "-",
        right: { type: 5 /* Name */, value: "foo" },
    });
    expect(parseExpr("not True")).toEqual({
        type: 6 /* UnaryOperator */,
        op: "not",
        right: { type: 2 /* Boolean */, value: true },
    });
});

test("can parse parenthesis", () => {
    expect(parseExpr("(1 + 2)")).toEqual({
        type: 7 /* BinaryOperator */,
        op: "+",
        left: { type: 0 /* Number */, value: 1 },
        right: { type: 0 /* Number */, value: 2 },
    });
});

test("can parse binary operators", () => {
    expect(parseExpr("1 < 2")).toEqual({
        type: 7 /* BinaryOperator */,
        op: "<",
        left: { type: 0 /* Number */, value: 1 },
        right: { type: 0 /* Number */, value: 2 },
    });
    expect(parseExpr('a + "foo"')).toEqual({
        type: 7 /* BinaryOperator */,
        op: "+",
        left: { type: 5 /* Name */, value: "a" },
        right: { type: 1 /* String */, value: "foo" },
    });
});

test("can parse boolean operators", () => {
    expect(parseExpr('True and "foo"')).toEqual({
        type: 14 /* BooleanOperator */,
        op: "and",
        left: { type: 2 /* Boolean */, value: true },
        right: { type: 1 /* String */, value: "foo" },
    });
    expect(parseExpr('True or "foo"')).toEqual({
        type: 14 /* BooleanOperator */,
        op: "or",
        left: { type: 2 /* Boolean */, value: true },
        right: { type: 1 /* String */, value: "foo" },
    });
});

test("expression with == and or", () => {
    expect(parseExpr("False == True and False")).toEqual({
        type: 14 /* BooleanOperator */,
        op: "and",
        left: {
            type: 7 /* BinaryOperator */,
            op: "==",
            left: { type: 2 /* Boolean */, value: false },
            right: { type: 2 /* Boolean */, value: true },
        },
        right: { type: 2 /* Boolean */, value: false },
    });
});

test("expression with + and ==", () => {
    expect(parseExpr("1 + 2 == 3")).toEqual({
        type: 7 /* BinaryOperator */,
        op: "==",
        left: {
            type: 7 /* BinaryOperator */,
            op: "+",
            left: { type: 0 /* Number */, value: 1 },
            right: { type: 0 /* Number */, value: 2 },
        },
        right: { type: 0 /* Number */, value: 3 },
    });
});

test("can parse chained comparisons", () => {
    expect(parseExpr("1 < 2 <= 3")).toEqual({
        type: 14 /* BooleanOperator */,
        op: "and",
        left: {
            type: 7 /* BinaryOperator */,
            op: "<",
            left: { type: 0 /* Number */, value: 1 },
            right: { type: 0 /* Number */, value: 2 },
        },
        right: {
            type: 7 /* BinaryOperator */,
            op: "<=",
            left: { type: 0 /* Number */, value: 2 },
            right: { type: 0 /* Number */, value: 3 },
        },
    });
    expect(parseExpr("1 < 2 <= 3 > 33")).toEqual({
        type: 14 /* BooleanOperator */,
        op: "and",
        left: {
            type: 14 /* BooleanOperator */,
            op: "and",
            left: {
                type: 7 /* BinaryOperator */,
                op: "<",
                left: { type: 0 /* Number */, value: 1 },
                right: { type: 0 /* Number */, value: 2 },
            },
            right: {
                type: 7 /* BinaryOperator */,
                op: "<=",
                left: { type: 0 /* Number */, value: 2 },
                right: { type: 0 /* Number */, value: 3 },
            },
        },
        right: {
            type: 7 /* BinaryOperator */,
            op: ">",
            left: { type: 0 /* Number */, value: 3 },
            right: { type: 0 /* Number */, value: 33 },
        },
    });
});

test("can parse lists", () => {
    expect(parseExpr("[]")).toEqual({
        type: 4 /* List */,
        value: [],
    });
    expect(parseExpr("[1]")).toEqual({
        type: 4 /* List */,
        value: [{ type: 0 /* Number */, value: 1 }],
    });
    expect(parseExpr("[1,]")).toEqual({
        type: 4 /* List */,
        value: [{ type: 0 /* Number */, value: 1 }],
    });
    expect(parseExpr("[1, 4]")).toEqual({
        type: 4 /* List */,
        value: [
            { type: 0 /* Number */, value: 1 },
            { type: 0 /* Number */, value: 4 },
        ],
    });
    expect(() => parseExpr("[1 1]")).toThrow();
});

test("can parse lists lookup", () => {
    expect(parseExpr("[1,2][1]")).toEqual({
        type: 12 /* Lookup */,
        target: {
            type: 4 /* List */,
            value: [
                { type: 0 /* Number */, value: 1 },
                { type: 0 /* Number */, value: 2 },
            ],
        },
        key: { type: 0 /* Number */, value: 1 },
    });
});

test("can parse tuples", () => {
    expect(parseExpr("()")).toEqual({
        type: 10 /* Tuple */,
        value: [],
    });
    expect(parseExpr("(1,)")).toEqual({
        type: 10 /* Tuple */,
        value: [{ type: 0 /* Number */, value: 1 }],
    });
    expect(parseExpr("(1,4)")).toEqual({
        type: 10 /* Tuple */,
        value: [
            { type: 0 /* Number */, value: 1 },
            { type: 0 /* Number */, value: 4 },
        ],
    });
    expect(() => parseExpr("(1 1)")).toThrow();
});

test("can parse dictionary", () => {
    expect(parseExpr("{}")).toEqual({
        type: 11 /* Dictionary */,
        value: {},
    });
    expect(parseExpr("{'foo': 1}")).toEqual({
        type: 11 /* Dictionary */,
        value: { foo: { type: 0 /* Number */, value: 1 } },
    });
    expect(parseExpr("{'foo': 1, 'bar': 3}")).toEqual({
        type: 11 /* Dictionary */,
        value: {
            foo: { type: 0 /* Number */, value: 1 },
            bar: { type: 0 /* Number */, value: 3 },
        },
    });
    expect(parseExpr("{1: 2}")).toEqual({
        type: 11 /* Dictionary */,
        value: { 1: { type: 0 /* Number */, value: 2 } },
    });
});

test("can parse dictionary lookup", () => {
    expect(parseExpr("{}['a']")).toEqual({
        type: 12 /* Lookup */,
        target: { type: 11 /* Dictionary */, value: {} },
        key: { type: 1 /* String */, value: "a" },
    });
});

test("can parse assignment", () => {
    expect(parseExpr("a=1")).toEqual({
        type: 9 /* Assignment */,
        name: { type: 5 /* Name */, value: "a" },
        value: { type: 0 /* Number */, value: 1 },
    });
});

test("can parse function calls", () => {
    expect(parseExpr("f()")).toEqual({
        type: 8 /* FunctionCall */,
        fn: { type: 5 /* Name */, value: "f" },
        args: [],
        kwargs: {},
    });
    expect(parseExpr("f() + 2")).toEqual({
        type: 7 /* BinaryOperator */,
        op: "+",
        left: {
            type: 8 /* FunctionCall */,
            fn: { type: 5 /* Name */, value: "f" },
            args: [],
            kwargs: {},
        },
        right: { type: 0 /* Number */, value: 2 },
    });
    expect(parseExpr("f(1)")).toEqual({
        type: 8 /* FunctionCall */,
        fn: { type: 5 /* Name */, value: "f" },
        args: [{ type: 0 /* Number */, value: 1 }],
        kwargs: {},
    });
    expect(parseExpr("f(1, 2)")).toEqual({
        type: 8 /* FunctionCall */,
        fn: { type: 5 /* Name */, value: "f" },
        args: [
            { type: 0 /* Number */, value: 1 },
            { type: 0 /* Number */, value: 2 },
        ],
        kwargs: {},
    });
});

test("can parse function calls with kwargs", () => {
    expect(parseExpr("f(a = 1)")).toEqual({
        type: 8 /* FunctionCall */,
        fn: { type: 5 /* Name */, value: "f" },
        args: [],
        kwargs: { a: { type: 0 /* Number */, value: 1 } },
    });
    expect(parseExpr("f(3, a = 1)")).toEqual({
        type: 8 /* FunctionCall */,
        fn: { type: 5 /* Name */, value: "f" },
        args: [{ type: 0 /* Number */, value: 3 }],
        kwargs: { a: { type: 0 /* Number */, value: 1 } },
    });
});

test("can parse not a in b", () => {
    expect(parseExpr("not a in b")).toEqual({
        type: 6 /* UnaryOperator */,
        op: "not",
        right: {
            type: 7 /* BinaryOperator */,
            op: "in",
            left: { type: 5 /* Name */, value: "a" },
            right: { type: 5 /* Name */, value: "b" },
        },
    });
    expect(parseExpr("a.b.c")).toEqual({
        type: 15 /* ObjLookup */,
        obj: {
            type: 15 /* ObjLookup */,
            obj: { type: 5 /* Name */, value: "a" },
            key: "b",
        },
        key: "c",
    });
});

test("can parse if statement", () => {
    expect(parseExpr("1 if True else 2")).toEqual({
        type: 13 /* If */,
        condition: { type: 2 /* Boolean */, value: true },
        ifTrue: { type: 0 /* Number */, value: 1 },
        ifFalse: { type: 0 /* Number */, value: 2 },
    });
    expect(parseExpr("1 + 1 if True else 2")).toEqual({
        type: 13 /* If */,
        condition: { type: 2 /* Boolean */, value: true },
        ifTrue: {
            type: 7 /* BinaryOperator */,
            op: "+",
            left: { type: 0 /* Number */, value: 1 },
            right: { type: 0 /* Number */, value: 1 },
        },
        ifFalse: { type: 0 /* Number */, value: 2 },
    });
});

test("tuple in list", () => {
    expect(parseExpr("[(1,2)]")).toEqual({
        type: 4 /* List */,
        value: [
            {
                type: 10 /* Tuple */,
                value: [
                    { type: 0 /* Number */, value: 1 },
                    { type: 0 /* Number */, value: 2 },
                ],
            },
        ],
    });
});

test("cannot parse []a", () => {
    expect(() => parseExpr("[]a")).toThrow(/Error: Token\(s\) unused/);
    expect(() => parseExpr("[]a b")).toThrow(/Error: Token\(s\) unused/);
});
