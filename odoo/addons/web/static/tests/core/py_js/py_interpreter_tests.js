/** @odoo-module **/

import { evaluateExpr, evaluateBooleanExpr } from "@web/core/py_js/py";

QUnit.module("py", {}, () => {
    QUnit.module("interpreter", () => {
        QUnit.module("basic values");

        QUnit.test("evaluate simple values", (assert) => {
            assert.strictEqual(evaluateExpr("12"), 12);
            assert.strictEqual(evaluateExpr('"foo"'), "foo");
        });

        QUnit.test("empty expression", (assert) => {
            assert.throws(() => evaluateExpr(""), /Error: Missing token/);
        });

        QUnit.test("numbers", (assert) => {
            assert.strictEqual(evaluateExpr("1.2"), 1.2);
            assert.strictEqual(evaluateExpr(".12"), 0.12);
            assert.strictEqual(evaluateExpr("0"), 0);
            assert.strictEqual(evaluateExpr("1.0"), 1);
            assert.strictEqual(evaluateExpr("-1.2"), -1.2);
            assert.strictEqual(evaluateExpr("-12"), -12);
            assert.strictEqual(evaluateExpr("+12"), 12);
        });

        QUnit.test("strings", (assert) => {
            assert.strictEqual(evaluateExpr('""'), "");
            assert.strictEqual(evaluateExpr('"foo"'), "foo");
            assert.strictEqual(evaluateExpr("'foo'"), "foo");
            assert.strictEqual(evaluateExpr("'FOO'.lower()"), "foo");
            assert.strictEqual(evaluateExpr("'foo'.upper()"), "FOO");
        });

        QUnit.test("boolean", (assert) => {
            assert.strictEqual(evaluateExpr("True"), true);
            assert.strictEqual(evaluateExpr("False"), false);
        });

        QUnit.test("lists", (assert) => {
            assert.deepEqual(evaluateExpr("[]"), []);
            assert.deepEqual(evaluateExpr("[1]"), [1]);
            assert.deepEqual(evaluateExpr("[1,2]"), [1, 2]);
            assert.deepEqual(evaluateExpr("[1,False, None, 'foo']"), [1, false, null, "foo"]);
            assert.deepEqual(evaluateExpr("[1,2 + 3]"), [1, 5]);
            assert.deepEqual(evaluateExpr("[1,2, 3][1]"), 2);
        });

        QUnit.test("None", (assert) => {
            assert.strictEqual(evaluateExpr("None"), null);
        });

        QUnit.test("Tuples", (assert) => {
            assert.deepEqual(evaluateExpr("()"), []);
            assert.deepEqual(evaluateExpr("(1,)"), [1]);
            assert.deepEqual(evaluateExpr("(1,2)"), [1, 2]);
        });

        QUnit.test("strings can be concatenated", (assert) => {
            assert.strictEqual(evaluateExpr('"foo" + "bar"'), "foobar");
        });

        QUnit.module("number properties");

        QUnit.test("number arithmetic", (assert) => {
            assert.strictEqual(evaluateExpr("1 + 2"), 3);
            assert.strictEqual(evaluateExpr("4 - 2"), 2);
            assert.strictEqual(evaluateExpr("4 * 2"), 8);
            assert.strictEqual(evaluateExpr("1.5 + 2"), 3.5);
            assert.strictEqual(evaluateExpr("1 + -1"), 0);
            assert.strictEqual(evaluateExpr("1 - 1"), 0);
            assert.strictEqual(evaluateExpr("1.5 - 2"), -0.5);
            assert.strictEqual(evaluateExpr("0 * 5"), 0);
            assert.strictEqual(evaluateExpr("1 + 3 * 5"), 16);
            assert.strictEqual(evaluateExpr("42 * -2"), -84);
            assert.strictEqual(evaluateExpr("1 / 2"), 0.5);
            assert.strictEqual(evaluateExpr("2 / 1"), 2);
            assert.strictEqual(evaluateExpr("42 % 5"), 2);
            assert.strictEqual(evaluateExpr("2 ** 3"), 8);
            assert.strictEqual(evaluateExpr("a + b", { a: 1, b: 41 }), 42);
        });

        QUnit.test("// operator", (assert) => {
            assert.strictEqual(evaluateExpr("1 // 2"), 0);
            assert.strictEqual(evaluateExpr("1 // -2"), -1);
            assert.strictEqual(evaluateExpr("-1 // 2"), -1);
            assert.strictEqual(evaluateExpr("6 // 2"), 3);
        });

        QUnit.module("boolean properties");

        QUnit.test("boolean arithmetic", (assert) => {
            assert.strictEqual(evaluateExpr("True and False"), false);
            assert.strictEqual(evaluateExpr("True or False"), true);
            assert.strictEqual(evaluateExpr("True and (False or True)"), true);
            assert.strictEqual(evaluateExpr("not True"), false);
            assert.strictEqual(evaluateExpr("not False"), true);
            assert.strictEqual(evaluateExpr("not foo", { foo: false }), true);
            assert.strictEqual(evaluateExpr("not None"), true);
            assert.strictEqual(evaluateExpr("not []"), true);
            assert.strictEqual(evaluateExpr("True == False or True == True"), true);
            assert.strictEqual(evaluateExpr("False == True and False"), false);
        });

        QUnit.test("get value from context", (assert) => {
            assert.strictEqual(evaluateExpr("foo == 'foo' or foo == 'bar'", { foo: "bar" }), true);
            assert.strictEqual(
                evaluateExpr("foo == 'foo' and bar == 'bar'", { foo: "foo", bar: "bar" }),
                true
            );
        });

        QUnit.test("should be lazy", (assert) => {
            // second clause should nameerror if evaluated
            assert.throws(() => evaluateExpr("foo == 'foo' and bar == 'bar'", { foo: "foo" }));
            assert.strictEqual(
                evaluateExpr("foo == 'foo' and bar == 'bar'", { foo: "bar" }),
                false
            );
            assert.strictEqual(evaluateExpr("foo == 'foo' or bar == 'bar'", { foo: "foo" }), true);
        });

        QUnit.test("should return the actual object", (assert) => {
            assert.strictEqual(evaluateExpr('"foo" or "bar"'), "foo");
            assert.strictEqual(evaluateExpr('None or "bar"'), "bar");
            assert.strictEqual(evaluateExpr("False or None"), null);
            assert.strictEqual(evaluateExpr("0 or 1"), 1);
            assert.strictEqual(evaluateExpr("[] or False"), false);
        });

        QUnit.module("values from context");

        QUnit.test("free variable", (assert) => {
            assert.strictEqual(evaluateExpr("a", { a: 3 }), 3);
            assert.strictEqual(evaluateExpr("a + b", { a: 3, b: 5 }), 8);
            assert.strictEqual(evaluateExpr("a", { a: true }), true);
            assert.strictEqual(evaluateExpr("a", { a: false }), false);
            assert.strictEqual(evaluateExpr("a", { a: null }), null);
            assert.strictEqual(evaluateExpr("a", { a: "bar" }), "bar");
            assert.deepEqual(evaluateExpr("foo", { foo: [1, 2, 3] }), [1, 2, 3]);
        });

        QUnit.test(
            "special case for context: the eval context can be accessed as 'context'",
            (assert) => {
                assert.strictEqual(evaluateExpr("context.get('b', 54)", { b: 3 }), 3);
                assert.strictEqual(evaluateExpr("context.get('c', 54)", { b: 3 }), 54);
            }
        );

        QUnit.test("true and false available in context", (assert) => {
            assert.strictEqual(evaluateExpr("true"), true);
            assert.strictEqual(evaluateExpr("false"), false);
        });

        QUnit.test("throw error if name is not defined", (assert) => {
            assert.throws(() => evaluateExpr("a"));
        });

        QUnit.module("comparisons");

        QUnit.test("equality", (assert) => {
            assert.strictEqual(evaluateExpr("1 == 1"), true);
            assert.strictEqual(evaluateExpr('"foo" == "foo"'), true);
            assert.strictEqual(evaluateExpr('"foo" == "bar"'), false);
            assert.strictEqual(evaluateExpr("1 == True"), true);
            assert.strictEqual(evaluateExpr("True == 1"), true);
            assert.strictEqual(evaluateExpr("1 == False"), false);
            assert.strictEqual(evaluateExpr("False == 1"), false);
            assert.strictEqual(evaluateExpr("0 == False"), true);
            assert.strictEqual(evaluateExpr("False == 0"), true);
            assert.strictEqual(evaluateExpr("None == None"), true);
            assert.strictEqual(evaluateExpr("None == False"), false);
        });

        QUnit.test("equality should work with free variables", (assert) => {
            assert.strictEqual(evaluateExpr("1 == a", { a: 1 }), true);
            assert.strictEqual(evaluateExpr('foo == "bar"', { foo: "bar" }), true);
            assert.strictEqual(evaluateExpr('foo == "bar"', { foo: "qux" }), false);
        });

        QUnit.test("inequality", (assert) => {
            assert.strictEqual(evaluateExpr("1 != 2"), true);
            assert.strictEqual(evaluateExpr('"foo" != "foo"'), false);
            assert.strictEqual(evaluateExpr('"foo" != "bar"'), true);
        });

        QUnit.test("inequality should work with free variables", (assert) => {
            assert.strictEqual(evaluateExpr("1 != a", { a: 42 }), true);
            assert.strictEqual(evaluateExpr('foo != "bar"', { foo: "bar" }), false);
            assert.strictEqual(evaluateExpr('foo != "bar"', { foo: "qux" }), true);
            assert.strictEqual(evaluateExpr("foo != bar", { foo: "qux", bar: "quux" }), true);
        });

        QUnit.test("should accept deprecated form", (assert) => {
            assert.strictEqual(evaluateExpr("1 <> 2"), true);
            assert.strictEqual(evaluateExpr('"foo" <> "foo"'), false);
            assert.strictEqual(evaluateExpr('"foo" <> "bar"'), true);
        });

        QUnit.test("comparing numbers", (assert) => {
            assert.strictEqual(evaluateExpr("3 < 5"), true);
            assert.strictEqual(evaluateExpr("3 > 5"), false);
            assert.strictEqual(evaluateExpr("5 >= 3"), true);
            assert.strictEqual(evaluateExpr("3 >= 3"), true);
            assert.strictEqual(evaluateExpr("3 <= 5"), true);
            assert.strictEqual(evaluateExpr("5 <= 3"), false);
        });

        QUnit.test("should support comparison chains", (assert) => {
            assert.strictEqual(evaluateExpr("1 < 3 < 5"), true);
            assert.strictEqual(evaluateExpr("5 > 3 > 1"), true);
            assert.strictEqual(evaluateExpr("1 < 3 > 2 == 2 > -2"), true);
            assert.strictEqual(evaluateExpr("1 < 2 < 3 < 4 < 5 < 6"), true);
        });

        QUnit.test("should compare strings", (assert) => {
            assert.strictEqual(
                evaluateExpr("date >= current", { date: "2010-06-08", current: "2010-06-05" }),
                true
            );
            assert.strictEqual(evaluateExpr('state >= "cancel"', { state: "cancel" }), true);
            assert.strictEqual(evaluateExpr('state >= "cancel"', { state: "open" }), true);
        });

        QUnit.test("mixed types comparisons", (assert) => {
            assert.strictEqual(evaluateExpr("None < 42"), true);
            assert.strictEqual(evaluateExpr("None > 42"), false);
            assert.strictEqual(evaluateExpr("42 > None"), true);
            assert.strictEqual(evaluateExpr("None < False"), true);
            assert.strictEqual(evaluateExpr("None < True"), true);
            assert.strictEqual(evaluateExpr("False > None"), true);
            assert.strictEqual(evaluateExpr("True > None"), true);
            assert.strictEqual(evaluateExpr("None > False"), false);
            assert.strictEqual(evaluateExpr("None > True"), false);
            assert.strictEqual(evaluateExpr("0 > True"), false);
            assert.strictEqual(evaluateExpr("0 < True"), true);
            assert.strictEqual(evaluateExpr("1 <= True"), true);
            assert.strictEqual(evaluateExpr('False < ""'), true);
            assert.strictEqual(evaluateExpr('"" > False'), true);
            assert.strictEqual(evaluateExpr('False > ""'), false);
            assert.strictEqual(evaluateExpr('0 < ""'), true);
            assert.strictEqual(evaluateExpr('"" > 0'), true);
            assert.strictEqual(evaluateExpr('0 > ""'), false);
            assert.strictEqual(evaluateExpr("3 < True"), false);
            assert.strictEqual(evaluateExpr("3 > True"), true);
            assert.strictEqual(evaluateExpr("{} > None"), true);
            assert.strictEqual(evaluateExpr("{} < None"), false);
            assert.strictEqual(evaluateExpr("{} > False"), true);
            assert.strictEqual(evaluateExpr("{} < False"), false);
            assert.strictEqual(evaluateExpr("3 < 'foo'"), true);
            assert.strictEqual(evaluateExpr("'foo' < 4444"), false);
            assert.strictEqual(evaluateExpr("{} < []"), true);
        });

        QUnit.module("containment");

        QUnit.test("in tuples", (assert) => {
            assert.strictEqual(evaluateExpr("'bar' in ('foo', 'bar')"), true);
            assert.strictEqual(evaluateExpr("'bar' in ('foo', 'qux')"), false);
            assert.strictEqual(evaluateExpr("1 in (1,2,3,4)"), true);
            assert.strictEqual(evaluateExpr("1 in (2,3,4)"), false);
            assert.strictEqual(evaluateExpr("'url' in ('url',)"), true);
            assert.strictEqual(evaluateExpr("'ur' in ('url',)"), false);
            assert.strictEqual(evaluateExpr("'url' in ('url', 'foo', 'bar')"), true);
        });

        QUnit.test("in strings", (assert) => {
            assert.strictEqual(evaluateExpr("'bar' in 'bar'"), true);
            assert.strictEqual(evaluateExpr("'bar' in 'foobar'"), true);
            assert.strictEqual(evaluateExpr("'bar' in 'fooqux'"), false);
        });

        QUnit.test("in lists", (assert) => {
            assert.strictEqual(evaluateExpr("'bar' in ['foo', 'bar']"), true);
            assert.strictEqual(evaluateExpr("'bar' in ['foo', 'qux']"), false);
            assert.strictEqual(evaluateExpr("3  in [1,2,3]"), true);
            assert.strictEqual(evaluateExpr("None  in [1,'foo',None]"), true);
            assert.strictEqual(evaluateExpr("not a in b", { a: 3, b: [1, 2, 4, 8] }), true);
        });

        QUnit.test("not in", (assert) => {
            assert.strictEqual(evaluateExpr("1  not in (2,3,4)"), true);
            assert.strictEqual(evaluateExpr('"ur" not in ("url",)'), true);
            assert.strictEqual(evaluateExpr("-2 not in (1,2,3)"), true);
            assert.strictEqual(evaluateExpr("-2 not in (1,-2,3)"), false);
        });

        QUnit.module("conversions");

        QUnit.test("to bool", (assert) => {
            assert.strictEqual(evaluateExpr("bool()"), false);
            assert.strictEqual(evaluateExpr("bool(0)"), false);
            assert.strictEqual(evaluateExpr("bool(1)"), true);
            assert.strictEqual(evaluateExpr("bool(False)"), false);
            assert.strictEqual(evaluateExpr("bool(True)"), true);
            assert.strictEqual(evaluateExpr("bool({})"), false);
            assert.strictEqual(evaluateExpr("bool({ 'a': 1 })"), true);
            assert.strictEqual(evaluateExpr("bool([])"), false);
            assert.strictEqual(evaluateExpr("bool([1])"), true);
            assert.strictEqual(evaluateExpr("bool('')"), false);
            assert.strictEqual(evaluateExpr("bool('foo')"), true);
            assert.strictEqual(evaluateExpr("bool(set())"), false);
            assert.strictEqual(evaluateExpr("bool(set([1]))"), true);
            assert.strictEqual(
                evaluateExpr("bool(date_deadline)", { date_deadline: "2008" }),
                true
            );
            assert.strictEqual(evaluateExpr("bool(s)", { s: "" }), false);
        });

        QUnit.module("callables");

        QUnit.test("should not call function from context", (assert) => {
            assert.throws(() => evaluateExpr("foo()", { foo: () => 3 }));
            assert.throws(() => evaluateExpr("1 + foo()", { foo: () => 3 }));
        });

        QUnit.module("dicts");

        QUnit.test("dict", (assert) => {
            assert.deepEqual(evaluateExpr("{}"), {});
            assert.deepEqual(evaluateExpr("{'foo': 1 + 2}"), { foo: 3 });
            assert.deepEqual(evaluateExpr("{'foo': 1, 'bar': 4}"), { foo: 1, bar: 4 });
        });

        QUnit.test("lookup and definition", (assert) => {
            assert.strictEqual(evaluateExpr("{'a': 1}['a']"), 1);
            assert.strictEqual(evaluateExpr("{1: 2}[1]"), 2);
        });

        QUnit.test("can get values with get method", (assert) => {
            assert.strictEqual(evaluateExpr("{'a': 1}.get('a')"), 1);
            assert.strictEqual(evaluateExpr("{'a': 1}.get('b')"), null);
            assert.strictEqual(evaluateExpr("{'a': 1}.get('b', 54)"), 54);
        });

        QUnit.test("can get values from values 'context'", (assert) => {
            assert.strictEqual(evaluateExpr("context.get('a')", { context: { a: 123 } }), 123);
            const values = { context: { a: { b: { c: 321 } } } };
            assert.strictEqual(evaluateExpr("context.get('a').b.c", values), 321);
            assert.strictEqual(evaluateExpr("context.get('a', {'e': 5}).b.c", values), 321);
            assert.strictEqual(evaluateExpr("context.get('d', 3)", values), 3);
            assert.strictEqual(evaluateExpr("context.get('d', {'e': 5})['e']", values), 5);
        });

        QUnit.test("can check if a key is in the 'context'", (assert) => {
            assert.strictEqual(evaluateExpr("'a' in context", { context: { a: 123 } }), true);
            assert.strictEqual(evaluateExpr("'a' in context", { context: { b: 123 } }), false);
            assert.strictEqual(evaluateExpr("'a' not in context", { context: { a: 123 } }), false);
            assert.strictEqual(evaluateExpr("'a' not in context", { context: { b: 123 } }), true);
        });

        QUnit.module("objects");

        QUnit.test("can read values from object", (assert) => {
            assert.strictEqual(evaluateExpr("obj.a", { obj: { a: 123 } }), 123);
            assert.strictEqual(evaluateExpr("obj.a.b.c", { obj: { a: { b: { c: 321 } } } }), 321);
        });

        QUnit.test("cannot call function in object", (assert) => {
            assert.throws(() => evaluateExpr("obj.f(3)", { obj: { f: (n) => n + 1 } }));
        });

        QUnit.module("if expressions");

        QUnit.test("simple if expressions", (assert) => {
            assert.strictEqual(evaluateExpr("1 if True else 2"), 1);
            assert.strictEqual(evaluateExpr("1 if 3 < 2 else 'greater'"), "greater");
        });

        QUnit.test("only evaluate proper branch", (assert) => {
            // will throw if evaluate wrong branch => name error
            assert.strictEqual(evaluateExpr("1 if True else boom"), 1);
            assert.strictEqual(evaluateExpr("boom if False else 222"), 222);
        });

        QUnit.module("miscellaneous expressions");

        QUnit.test("tuple in list", (assert) => {
            assert.deepEqual(evaluateExpr("[(1 + 2,'foo', True)]"), [[3, "foo", true]]);
        });

        QUnit.module("evaluate to boolean");

        QUnit.test("simple expression", (assert) => {
            assert.strictEqual(evaluateBooleanExpr("12"), true);
            assert.strictEqual(evaluateBooleanExpr("0"), false);
            assert.strictEqual(evaluateBooleanExpr("0 + 3 - 1"), true);
            assert.strictEqual(evaluateBooleanExpr("0 + 3 - 1 - 2"), false);
            assert.strictEqual(evaluateBooleanExpr('"foo"'), true);
            assert.strictEqual(evaluateBooleanExpr("[1]"), true);
            assert.strictEqual(evaluateBooleanExpr("[]"), false);
        });

        QUnit.test("use contextual values", (assert) => {
            assert.strictEqual(evaluateBooleanExpr("a", { a: 12 }), true);
            assert.strictEqual(evaluateBooleanExpr("a", { a: 0 }), false);
            assert.strictEqual(evaluateBooleanExpr("0 + 3 - a", { a: 1 }), true);
            assert.strictEqual(evaluateBooleanExpr("0 + 3 - a - 2", { a: 1 }), false);
            assert.strictEqual(evaluateBooleanExpr("0 + 3 - a - b", { a: 1, b: 2 }), false);
            assert.strictEqual(evaluateBooleanExpr("a", { a: "foo" }), true);
            assert.strictEqual(evaluateBooleanExpr("a", { a: [1] }), true);
            assert.strictEqual(evaluateBooleanExpr("a", { a: [] }), false);
        });

        QUnit.test("throw if has missing value", (assert) => {
            assert.throws(() => evaluateBooleanExpr("a", { b: 0 }));
            assert.strictEqual(evaluateBooleanExpr("1 or a"), true); // do not throw (lazy value)
            assert.throws(() => evaluateBooleanExpr("0 or a"));
            assert.throws(() => evaluateBooleanExpr("a or b", { b: true }));
            assert.throws(() => evaluateBooleanExpr("a and b", { b: true }));
            assert.throws(() => evaluateBooleanExpr("a()"));
            assert.throws(() => evaluateBooleanExpr("a[0]"));
            assert.throws(() => evaluateBooleanExpr("a.b"));
            assert.throws(() => evaluateBooleanExpr("0 + 3 - a", { b: 1 }));
            assert.throws(() => evaluateBooleanExpr("0 + 3 - a - 2", { b: 1 }));
            assert.throws(() => evaluateBooleanExpr("0 + 3 - a - b", { b: 2 }));
        });

        QUnit.module("sets");

        QUnit.test("static set", (assert) => {
            assert.deepEqual(evaluateExpr("set()"), new Set());
            assert.deepEqual(evaluateExpr("set([])"), new Set([]));
            assert.deepEqual(evaluateExpr("set([0])"), new Set([0]));
            assert.deepEqual(evaluateExpr("set([1])"), new Set([1]));
            assert.deepEqual(evaluateExpr("set([0, 0])"), new Set([0]));
            assert.deepEqual(evaluateExpr("set([0, 1])"), new Set([0, 1]));
            assert.deepEqual(evaluateExpr("set([1, 1])"), new Set([1]));

            assert.deepEqual(evaluateExpr("set('')"), new Set());
            assert.deepEqual(evaluateExpr("set('a')"), new Set(["a"]));
            assert.deepEqual(evaluateExpr("set('ab')"), new Set(["a", "b"]));

            assert.deepEqual(evaluateExpr("set({})"), new Set());
            assert.deepEqual(evaluateExpr("set({ 'a': 1 })"), new Set(["a"]));
            assert.deepEqual(evaluateExpr("set({ '': 1, 'a': 1 })"), new Set(["", "a"]));

            assert.throws(() => evaluateExpr("set(0)"));
            assert.throws(() => evaluateExpr("set(1)"));
            assert.throws(() => evaluateExpr("set(None)"));
            assert.throws(() => evaluateExpr("set(false)"));
            assert.throws(() => evaluateExpr("set(true)"));
            assert.throws(() => evaluateExpr("set(1, 2)"));

            assert.throws(() => evaluateExpr("set(expr)", { expr: undefined }));
            assert.throws(() => evaluateExpr("set(expr)", { expr: null }));

            assert.throws(() => evaluateExpr("set([], [])")); // valid but not supported by py_js

            assert.throws(() => evaluateExpr("set({ 'a' })")); // valid but not supported by py_js
        });

        QUnit.test("set intersection", (assert) => {
            assert.deepEqual(evaluateExpr("set([1,2,3]).intersection()"), new Set([1, 2, 3]));
            assert.deepEqual(
                evaluateExpr("set([1,2,3]).intersection(set([2,3]))"),
                new Set([2, 3])
            );
            assert.deepEqual(evaluateExpr("set([1,2,3]).intersection([2,3])"), new Set([2, 3]));
            assert.deepEqual(
                evaluateExpr("set([1,2,3]).intersection(r)", { r: [2, 3] }),
                new Set([2, 3])
            );
            assert.deepEqual(
                evaluateExpr("r.intersection([2,3])", { r: new Set([1, 2, 3, 2]) }),
                new Set([2, 3])
            );

            assert.deepEqual(
                evaluateExpr("set(foo_ids).intersection([2,3])", { foo_ids: [1, 2] }),
                new Set([2])
            );
            assert.deepEqual(
                evaluateExpr("set(foo_ids).intersection([2,3])", { foo_ids: [1] }),
                new Set()
            );
            assert.deepEqual(
                evaluateExpr("set([foo_id]).intersection([2,3])", { foo_id: 1 }),
                new Set()
            );
            assert.deepEqual(
                evaluateExpr("set([foo_id]).intersection([2,3])", { foo_id: 2 }),
                new Set([2])
            );

            assert.throws(() => evaluateExpr("set([]).intersection([], [])")); // valid but not supported by py_js
            assert.throws(() => evaluateExpr("set([]).intersection([], [], [])")); // valid but not supported by py_js
        });

        QUnit.test("set difference", (assert) => {
            assert.deepEqual(evaluateExpr("set([1,2,3]).difference()"), new Set([1, 2, 3]));
            assert.deepEqual(evaluateExpr("set([1,2,3]).difference(set([2,3]))"), new Set([1]));
            assert.deepEqual(evaluateExpr("set([1,2,3]).difference([2,3])"), new Set([1]));
            assert.deepEqual(
                evaluateExpr("set([1,2,3]).difference(r)", { r: [2, 3] }),
                new Set([1])
            );
            assert.deepEqual(
                evaluateExpr("r.difference([2,3])", { r: new Set([1, 2, 3, 2, 4]) }),
                new Set([1, 4])
            );

            assert.deepEqual(
                evaluateExpr("set(foo_ids).difference([2,3])", { foo_ids: [1, 2] }),
                new Set([1])
            );
            assert.deepEqual(
                evaluateExpr("set(foo_ids).difference([2,3])", { foo_ids: [1] }),
                new Set([1])
            );
            assert.deepEqual(
                evaluateExpr("set([foo_id]).difference([2,3])", { foo_id: 1 }),
                new Set([1])
            );
            assert.deepEqual(
                evaluateExpr("set([foo_id]).difference([2,3])", { foo_id: 2 }),
                new Set()
            );

            assert.throws(() => evaluateExpr("set([]).difference([], [])")); // valid but not supported by py_js
            assert.throws(() => evaluateExpr("set([]).difference([], [], [])")); // valid but not supported by py_js
        });

        QUnit.test("set union", (assert) => {
            assert.deepEqual(evaluateExpr("set([1,2,3]).union()"), new Set([1, 2, 3]));
            assert.deepEqual(
                evaluateExpr("set([1,2,3]).union(set([2,3,4]))"),
                new Set([1, 2, 3, 4])
            );
            assert.deepEqual(evaluateExpr("set([1,2,3]).union([2,4])"), new Set([1, 2, 3, 4]));
            assert.deepEqual(
                evaluateExpr("set([1,2,3]).union(r)", { r: [2, 4] }),
                new Set([1, 2, 3, 4])
            );
            assert.deepEqual(
                evaluateExpr("r.union([2,3])", { r: new Set([1, 2, 2, 4]) }),
                new Set([1, 2, 3, 4])
            );

            assert.deepEqual(
                evaluateExpr("set(foo_ids).union([2,3])", { foo_ids: [1, 2] }),
                new Set([1, 2, 3])
            );
            assert.deepEqual(
                evaluateExpr("set(foo_ids).union([2,3])", { foo_ids: [1] }),
                new Set([1, 2, 3])
            );
            assert.deepEqual(
                evaluateExpr("set([foo_id]).union([2,3])", { foo_id: 1 }),
                new Set([1, 2, 3])
            );
            assert.deepEqual(
                evaluateExpr("set([foo_id]).union([2,3])", { foo_id: 2 }),
                new Set([2, 3])
            );

            assert.throws(() => evaluateExpr("set([]).union([], [])")); // valid but not supported by py_js
            assert.throws(() => evaluateExpr("set([]).union([], [], [])")); // valid but not supported by py_js
        });
    });
});
