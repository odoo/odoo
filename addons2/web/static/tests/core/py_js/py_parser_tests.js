/** @odoo-module **/

import { parseExpr } from "@web/core/py_js/py";

QUnit.module("py", {}, () => {
    QUnit.module("parser");

    QUnit.test("can parse basic elements", (assert) => {
        assert.deepEqual(parseExpr("1"), { type: 0 /* Number */, value: 1 });
        assert.deepEqual(parseExpr('"foo"'), { type: 1 /* String */, value: "foo" });
        assert.deepEqual(parseExpr("foo"), { type: 5 /* Name */, value: "foo" });
        assert.deepEqual(parseExpr("True"), { type: 2 /* Boolean */, value: true });
        assert.deepEqual(parseExpr("False"), { type: 2 /* Boolean */, value: false });
        assert.deepEqual(parseExpr("None"), { type: 3 /* None */ });
    });

    QUnit.test("cannot parse empty string", (assert) => {
        assert.throws(() => parseExpr(""), /Error: Missing token/);
    });

    QUnit.test("can parse unary operator -", (assert) => {
        assert.deepEqual(parseExpr("-1"), {
            type: 6 /* UnaryOperator */,
            op: "-",
            right: { type: 0 /* Number */, value: 1 },
        });
        assert.deepEqual(parseExpr("-foo"), {
            type: 6 /* UnaryOperator */,
            op: "-",
            right: { type: 5 /* Name */, value: "foo" },
        });
        assert.deepEqual(parseExpr("not True"), {
            type: 6 /* UnaryOperator */,
            op: "not",
            right: { type: 2 /* Boolean */, value: true },
        });
    });

    QUnit.test("can parse parenthesis", (assert) => {
        assert.deepEqual(parseExpr("(1 + 2)"), {
            type: 7 /* BinaryOperator */,
            op: "+",
            left: { type: 0 /* Number */, value: 1 },
            right: { type: 0 /* Number */, value: 2 },
        });
    });

    QUnit.test("can parse binary operators", (assert) => {
        assert.deepEqual(parseExpr("1 < 2"), {
            type: 7 /* BinaryOperator */,
            op: "<",
            left: { type: 0 /* Number */, value: 1 },
            right: { type: 0 /* Number */, value: 2 },
        });
        assert.deepEqual(parseExpr('a + "foo"'), {
            type: 7 /* BinaryOperator */,
            op: "+",
            left: { type: 5 /* Name */, value: "a" },
            right: { type: 1 /* String */, value: "foo" },
        });
    });

    QUnit.test("can parse boolean operators", (assert) => {
        assert.deepEqual(parseExpr('True and "foo"'), {
            type: 14 /* BooleanOperator */,
            op: "and",
            left: { type: 2 /* Boolean */, value: true },
            right: { type: 1 /* String */, value: "foo" },
        });
        assert.deepEqual(parseExpr('True or "foo"'), {
            type: 14 /* BooleanOperator */,
            op: "or",
            left: { type: 2 /* Boolean */, value: true },
            right: { type: 1 /* String */, value: "foo" },
        });
    });

    QUnit.test("expression with == and or", (assert) => {
        assert.deepEqual(parseExpr("False == True and False"), {
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

    QUnit.test("expression with + and ==", (assert) => {
        assert.deepEqual(parseExpr("1 + 2 == 3"), {
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

    QUnit.test("can parse chained comparisons", (assert) => {
        assert.deepEqual(parseExpr("1 < 2 <= 3"), {
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
        assert.deepEqual(parseExpr("1 < 2 <= 3 > 33"), {
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

    QUnit.test("can parse lists", (assert) => {
        assert.deepEqual(parseExpr("[]"), {
            type: 4 /* List */,
            value: [],
        });
        assert.deepEqual(parseExpr("[1]"), {
            type: 4 /* List */,
            value: [{ type: 0 /* Number */, value: 1 }],
        });
        assert.deepEqual(parseExpr("[1,]"), {
            type: 4 /* List */,
            value: [{ type: 0 /* Number */, value: 1 }],
        });
        assert.deepEqual(parseExpr("[1, 4]"), {
            type: 4 /* List */,
            value: [
                { type: 0 /* Number */, value: 1 },
                { type: 0 /* Number */, value: 4 },
            ],
        });
        assert.throws(() => parseExpr("[1 1]"));
    });

    QUnit.test("can parse lists lookup", (assert) => {
        assert.deepEqual(parseExpr("[1,2][1]"), {
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

    QUnit.test("can parse tuples", (assert) => {
        assert.deepEqual(parseExpr("()"), {
            type: 10 /* Tuple */,
            value: [],
        });
        assert.deepEqual(parseExpr("(1,)"), {
            type: 10 /* Tuple */,
            value: [{ type: 0 /* Number */, value: 1 }],
        });
        assert.deepEqual(parseExpr("(1,4)"), {
            type: 10 /* Tuple */,
            value: [
                { type: 0 /* Number */, value: 1 },
                { type: 0 /* Number */, value: 4 },
            ],
        });
        assert.throws(() => parseExpr("(1 1)"));
    });

    QUnit.test("can parse dictionary", (assert) => {
        assert.deepEqual(parseExpr("{}"), {
            type: 11 /* Dictionary */,
            value: {},
        });
        assert.deepEqual(parseExpr("{'foo': 1}"), {
            type: 11 /* Dictionary */,
            value: { foo: { type: 0 /* Number */, value: 1 } },
        });
        assert.deepEqual(parseExpr("{'foo': 1, 'bar': 3}"), {
            type: 11 /* Dictionary */,
            value: {
                foo: { type: 0 /* Number */, value: 1 },
                bar: { type: 0 /* Number */, value: 3 },
            },
        });
        assert.deepEqual(parseExpr("{1: 2}"), {
            type: 11 /* Dictionary */,
            value: { 1: { type: 0 /* Number */, value: 2 } },
        });
    });

    QUnit.test("can parse dictionary lookup", (assert) => {
        assert.deepEqual(parseExpr("{}['a']"), {
            type: 12 /* Lookup */,
            target: { type: 11 /* Dictionary */, value: {} },
            key: { type: 1 /* String */, value: "a" },
        });
    });

    QUnit.test("can parse assignment", (assert) => {
        assert.deepEqual(parseExpr("a=1"), {
            type: 9 /* Assignment */,
            name: { type: 5 /* Name */, value: "a" },
            value: { type: 0 /* Number */, value: 1 },
        });
    });

    QUnit.test("can parse function calls", (assert) => {
        assert.deepEqual(parseExpr("f()"), {
            type: 8 /* FunctionCall */,
            fn: { type: 5 /* Name */, value: "f" },
            args: [],
            kwargs: {},
        });
        assert.deepEqual(parseExpr("f() + 2"), {
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
        assert.deepEqual(parseExpr("f(1)"), {
            type: 8 /* FunctionCall */,
            fn: { type: 5 /* Name */, value: "f" },
            args: [{ type: 0 /* Number */, value: 1 }],
            kwargs: {},
        });
        assert.deepEqual(parseExpr("f(1, 2)"), {
            type: 8 /* FunctionCall */,
            fn: { type: 5 /* Name */, value: "f" },
            args: [
                { type: 0 /* Number */, value: 1 },
                { type: 0 /* Number */, value: 2 },
            ],
            kwargs: {},
        });
    });

    QUnit.test("can parse function calls with kwargs", (assert) => {
        assert.deepEqual(parseExpr("f(a = 1)"), {
            type: 8 /* FunctionCall */,
            fn: { type: 5 /* Name */, value: "f" },
            args: [],
            kwargs: { a: { type: 0 /* Number */, value: 1 } },
        });
        assert.deepEqual(parseExpr("f(3, a = 1)"), {
            type: 8 /* FunctionCall */,
            fn: { type: 5 /* Name */, value: "f" },
            args: [{ type: 0 /* Number */, value: 3 }],
            kwargs: { a: { type: 0 /* Number */, value: 1 } },
        });
    });

    QUnit.test("can parse not a in b", (assert) => {
        assert.deepEqual(parseExpr("not a in b"), {
            type: 6 /* UnaryOperator */,
            op: "not",
            right: {
                type: 7 /* BinaryOperator */,
                op: "in",
                left: { type: 5 /* Name */, value: "a" },
                right: { type: 5 /* Name */, value: "b" },
            },
        });
        assert.deepEqual(parseExpr("a.b.c"), {
            type: 15 /* ObjLookup */,
            obj: {
                type: 15 /* ObjLookup */,
                obj: { type: 5 /* Name */, value: "a" },
                key: "b",
            },
            key: "c",
        });
    });

    QUnit.test("can parse if statement", (assert) => {
        assert.deepEqual(parseExpr("1 if True else 2"), {
            type: 13 /* If */,
            condition: { type: 2 /* Boolean */, value: true },
            ifTrue: { type: 0 /* Number */, value: 1 },
            ifFalse: { type: 0 /* Number */, value: 2 },
        });
        assert.deepEqual(parseExpr("1 + 1 if True else 2"), {
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

    QUnit.test("tuple in list", (assert) => {
        assert.deepEqual(parseExpr("[(1,2)]"), {
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
});
