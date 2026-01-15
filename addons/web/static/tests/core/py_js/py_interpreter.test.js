import { describe, expect, test } from "@odoo/hoot";

import { evaluateBooleanExpr, evaluateExpr } from "@web/core/py_js/py";

describe.current.tags("headless");

describe("basic values", () => {
    test("evaluate simple values", () => {
        expect(evaluateExpr("12")).toBe(12);
        expect(evaluateExpr('"foo"')).toBe("foo");
    });

    test("empty expression", () => {
        expect(() => evaluateExpr("")).toThrow(/Error: Missing token/);
    });

    test("numbers", () => {
        expect(evaluateExpr("1.2")).toBe(1.2);
        expect(evaluateExpr(".12")).toBe(0.12);
        expect(evaluateExpr("0")).toBe(0);
        expect(evaluateExpr("1.0")).toBe(1);
        expect(evaluateExpr("-1.2")).toBe(-1.2);
        expect(evaluateExpr("-12")).toBe(-12);
        expect(evaluateExpr("+12")).toBe(12);
    });

    test("strings", () => {
        expect(evaluateExpr('""')).toBe("");
        expect(evaluateExpr('"foo"')).toBe("foo");
        expect(evaluateExpr("'foo'")).toBe("foo");
        expect(evaluateExpr("'FOO'.lower()")).toBe("foo");
        expect(evaluateExpr("'foo'.upper()")).toBe("FOO");
    });

    test("boolean", () => {
        expect(evaluateExpr("True")).toBe(true);
        expect(evaluateExpr("False")).toBe(false);
    });

    test("lists", () => {
        expect(evaluateExpr("[]")).toEqual([]);
        expect(evaluateExpr("[1]")).toEqual([1]);
        expect(evaluateExpr("[1,2]")).toEqual([1, 2]);
        expect(evaluateExpr("[1,False, None, 'foo']")).toEqual([1, false, null, "foo"]);
        expect(evaluateExpr("[1,2 + 3]")).toEqual([1, 5]);
        expect(evaluateExpr("[1,2, 3][1]")).toBe(2);
    });

    test("None", () => {
        expect(evaluateExpr("None")).toBe(null);
    });

    test("Tuples", () => {
        expect(evaluateExpr("()")).toEqual([]);
        expect(evaluateExpr("(1,)")).toEqual([1]);
        expect(evaluateExpr("(1,2)")).toEqual([1, 2]);
    });

    test("strings can be concatenated", () => {
        expect(evaluateExpr('"foo" + "bar"')).toBe("foobar");
    });
});

describe("number properties", () => {
    test("number arithmetic", () => {
        expect(evaluateExpr("1 + 2")).toBe(3);
        expect(evaluateExpr("4 - 2")).toBe(2);
        expect(evaluateExpr("4 * 2")).toBe(8);
        expect(evaluateExpr("1.5 + 2")).toBe(3.5);
        expect(evaluateExpr("1 + -1")).toBe(0);
        expect(evaluateExpr("1 - 1")).toBe(0);
        expect(evaluateExpr("1.5 - 2")).toBe(-0.5);
        expect(evaluateExpr("0 * 5")).toBe(0);
        expect(evaluateExpr("1 + 3 * 5")).toBe(16);
        expect(evaluateExpr("42 * -2")).toBe(-84);
        expect(evaluateExpr("1 / 2")).toBe(0.5);
        expect(evaluateExpr("2 / 1")).toBe(2);
        expect(evaluateExpr("42 % 5")).toBe(2);
        expect(evaluateExpr("2 ** 3")).toBe(8);
        expect(evaluateExpr("a + b", { a: 1, b: 41 })).toBe(42);
    });

    test("// operator", () => {
        expect(evaluateExpr("1 // 2")).toBe(0);
        expect(evaluateExpr("1 // -2")).toBe(-1);
        expect(evaluateExpr("-1 // 2")).toBe(-1);
        expect(evaluateExpr("6 // 2")).toBe(3);
    });
});

describe("boolean properties", () => {
    test("boolean arithmetic", () => {
        expect(evaluateExpr("True and False")).toBe(false);
        expect(evaluateExpr("True or False")).toBe(true);
        expect(evaluateExpr("True and (False or True)")).toBe(true);
        expect(evaluateExpr("not True")).toBe(false);
        expect(evaluateExpr("not False")).toBe(true);
        expect(evaluateExpr("not foo", { foo: false })).toBe(true);
        expect(evaluateExpr("not None")).toBe(true);
        expect(evaluateExpr("not []")).toBe(true);
        expect(evaluateExpr("True == False or True == True")).toBe(true);
        expect(evaluateExpr("False == True and False")).toBe(false);
    });

    test("get value from context", () => {
        expect(evaluateExpr("foo == 'foo' or foo == 'bar'", { foo: "bar" })).toBe(true);
        expect(evaluateExpr("foo == 'foo' and bar == 'bar'", { foo: "foo", bar: "bar" })).toBe(
            true
        );
    });

    test("should be lazy", () => {
        // second clause should nameerror if evaluated
        expect(() => evaluateExpr("foo == 'foo' and bar == 'bar'", { foo: "foo" })).toThrow();
        expect(evaluateExpr("foo == 'foo' and bar == 'bar'", { foo: "bar" })).toBe(false);
        expect(evaluateExpr("foo == 'foo' or bar == 'bar'", { foo: "foo" })).toBe(true);
    });

    test("should return the actual object", () => {
        expect(evaluateExpr('"foo" or "bar"')).toBe("foo");
        expect(evaluateExpr('None or "bar"')).toBe("bar");
        expect(evaluateExpr("False or None")).toBe(null);
        expect(evaluateExpr("0 or 1")).toBe(1);
        expect(evaluateExpr("[] or False")).toBe(false);
    });
});

describe("values from context", () => {
    test("free variable", () => {
        expect(evaluateExpr("a", { a: 3 })).toBe(3);
        expect(evaluateExpr("a + b", { a: 3, b: 5 })).toBe(8);
        expect(evaluateExpr("a", { a: true })).toBe(true);
        expect(evaluateExpr("a", { a: false })).toBe(false);
        expect(evaluateExpr("a", { a: null })).toBe(null);
        expect(evaluateExpr("a", { a: "bar" })).toBe("bar");
        expect(evaluateExpr("foo", { foo: [1, 2, 3] })).toEqual([1, 2, 3]);
    });

    test("special case for context: the eval context can be accessed as 'context'", () => {
        expect(evaluateExpr("context.get('b', 54)", { b: 3 })).toBe(3);
        expect(evaluateExpr("context.get('c', 54)", { b: 3 })).toBe(54);
    });

    test("true and false available in context", () => {
        expect(evaluateExpr("true")).toBe(true);
        expect(evaluateExpr("false")).toBe(false);
    });

    test("throw error if name is not defined", () => {
        expect(() => evaluateExpr("a")).toThrow();
    });
});

describe("comparisons", () => {
    test("equality", () => {
        expect(evaluateExpr("1 == 1")).toBe(true);
        expect(evaluateExpr('"foo" == "foo"')).toBe(true);
        expect(evaluateExpr('"foo" == "bar"')).toBe(false);
        expect(evaluateExpr("1 == True")).toBe(true);
        expect(evaluateExpr("True == 1")).toBe(true);
        expect(evaluateExpr("1 == False")).toBe(false);
        expect(evaluateExpr("False == 1")).toBe(false);
        expect(evaluateExpr("0 == False")).toBe(true);
        expect(evaluateExpr("False == 0")).toBe(true);
        expect(evaluateExpr("None == None")).toBe(true);
        expect(evaluateExpr("None == False")).toBe(false);
    });

    test("equality should work with free variables", () => {
        expect(evaluateExpr("1 == a", { a: 1 })).toBe(true);
        expect(evaluateExpr('foo == "bar"', { foo: "bar" })).toBe(true);
        expect(evaluateExpr('foo == "bar"', { foo: "qux" })).toBe(false);
    });

    test("inequality", () => {
        expect(evaluateExpr("1 != 2")).toBe(true);
        expect(evaluateExpr('"foo" != "foo"')).toBe(false);
        expect(evaluateExpr('"foo" != "bar"')).toBe(true);
    });

    test("inequality should work with free variables", () => {
        expect(evaluateExpr("1 != a", { a: 42 })).toBe(true);
        expect(evaluateExpr('foo != "bar"', { foo: "bar" })).toBe(false);
        expect(evaluateExpr('foo != "bar"', { foo: "qux" })).toBe(true);
        expect(evaluateExpr("foo != bar", { foo: "qux", bar: "quux" })).toBe(true);
    });

    test("should accept deprecated form", () => {
        expect(evaluateExpr("1 <> 2")).toBe(true);
        expect(evaluateExpr('"foo" <> "foo"')).toBe(false);
        expect(evaluateExpr('"foo" <> "bar"')).toBe(true);
    });

    test("comparing numbers", () => {
        expect(evaluateExpr("3 < 5")).toBe(true);
        expect(evaluateExpr("3 > 5")).toBe(false);
        expect(evaluateExpr("5 >= 3")).toBe(true);
        expect(evaluateExpr("3 >= 3")).toBe(true);
        expect(evaluateExpr("3 <= 5")).toBe(true);
        expect(evaluateExpr("5 <= 3")).toBe(false);
    });

    test("should support comparison chains", () => {
        expect(evaluateExpr("1 < 3 < 5")).toBe(true);
        expect(evaluateExpr("5 > 3 > 1")).toBe(true);
        expect(evaluateExpr("1 < 3 > 2 == 2 > -2")).toBe(true);
        expect(evaluateExpr("1 < 2 < 3 < 4 < 5 < 6")).toBe(true);
    });

    test("should compare strings", () => {
        expect(evaluateExpr("date >= current", { date: "2010-06-08", current: "2010-06-05" })).toBe(
            true
        );
        expect(evaluateExpr('state >= "cancel"', { state: "cancel" })).toBe(true);
        expect(evaluateExpr('state >= "cancel"', { state: "open" })).toBe(true);
    });

    test("mixed types comparisons", () => {
        expect(evaluateExpr("None < 42")).toBe(true);
        expect(evaluateExpr("None > 42")).toBe(false);
        expect(evaluateExpr("42 > None")).toBe(true);
        expect(evaluateExpr("None < False")).toBe(true);
        expect(evaluateExpr("None < True")).toBe(true);
        expect(evaluateExpr("False > None")).toBe(true);
        expect(evaluateExpr("True > None")).toBe(true);
        expect(evaluateExpr("None > False")).toBe(false);
        expect(evaluateExpr("None > True")).toBe(false);
        expect(evaluateExpr("0 > True")).toBe(false);
        expect(evaluateExpr("0 < True")).toBe(true);
        expect(evaluateExpr("1 <= True")).toBe(true);
        expect(evaluateExpr('False < ""')).toBe(true);
        expect(evaluateExpr('"" > False')).toBe(true);
        expect(evaluateExpr('False > ""')).toBe(false);
        expect(evaluateExpr('0 < ""')).toBe(true);
        expect(evaluateExpr('"" > 0')).toBe(true);
        expect(evaluateExpr('0 > ""')).toBe(false);
        expect(evaluateExpr("3 < True")).toBe(false);
        expect(evaluateExpr("3 > True")).toBe(true);
        expect(evaluateExpr("{} > None")).toBe(true);
        expect(evaluateExpr("{} < None")).toBe(false);
        expect(evaluateExpr("{} > False")).toBe(true);
        expect(evaluateExpr("{} < False")).toBe(false);
        expect(evaluateExpr("3 < 'foo'")).toBe(true);
        expect(evaluateExpr("'foo' < 4444")).toBe(false);
        expect(evaluateExpr("{} < []")).toBe(true);
    });
});

describe("containment", () => {
    test("in tuples", () => {
        expect(evaluateExpr("'bar' in ('foo', 'bar')")).toBe(true);
        expect(evaluateExpr("'bar' in ('foo', 'qux')")).toBe(false);
        expect(evaluateExpr("1 in (1,2,3,4)")).toBe(true);
        expect(evaluateExpr("1 in (2,3,4)")).toBe(false);
        expect(evaluateExpr("'url' in ('url',)")).toBe(true);
        expect(evaluateExpr("'ur' in ('url',)")).toBe(false);
        expect(evaluateExpr("'url' in ('url', 'foo', 'bar')")).toBe(true);
    });

    test("in strings", () => {
        expect(evaluateExpr("'bar' in 'bar'")).toBe(true);
        expect(evaluateExpr("'bar' in 'foobar'")).toBe(true);
        expect(evaluateExpr("'bar' in 'fooqux'")).toBe(false);
    });

    test("in lists", () => {
        expect(evaluateExpr("'bar' in ['foo', 'bar']")).toBe(true);
        expect(evaluateExpr("'bar' in ['foo', 'qux']")).toBe(false);
        expect(evaluateExpr("3  in [1,2,3]")).toBe(true);
        expect(evaluateExpr("None  in [1,'foo',None]")).toBe(true);
        expect(evaluateExpr("not a in b", { a: 3, b: [1, 2, 4, 8] })).toBe(true);
    });

    test("not in", () => {
        expect(evaluateExpr("1  not in (2,3,4)")).toBe(true);
        expect(evaluateExpr('"ur" not in ("url",)')).toBe(true);
        expect(evaluateExpr("-2 not in (1,2,3)")).toBe(true);
        expect(evaluateExpr("-2 not in (1,-2,3)")).toBe(false);
    });
});

describe("conversions", () => {
    test("to bool", () => {
        expect(evaluateExpr("bool('')")).toBe(false);
        expect(evaluateExpr("bool('foo')")).toBe(true);
        expect(evaluateExpr("bool(date_deadline)", { date_deadline: "2008" })).toBe(true);
        expect(evaluateExpr("bool(s)", { s: "" })).toBe(false);
    });
});

describe("callables", () => {
    test("should not call function from context", () => {
        expect(() => evaluateExpr("foo()", { foo: () => 3 })).toThrow();
        expect(() => evaluateExpr("1 + foo()", { foo: () => 3 })).toThrow();
    });
    test("min/max", () => {
        expect(evaluateExpr("max(3, 5)")).toBe(5);
        expect(evaluateExpr("min(3, 5, 2, 7)")).toBe(2);
    });
});

describe("dicts", () => {
    test("dict", () => {
        expect(evaluateExpr("{}")).toEqual({});
        expect(evaluateExpr("{'foo': 1 + 2}")).toEqual({ foo: 3 });
        expect(evaluateExpr("{'foo': 1, 'bar': 4}")).toEqual({ foo: 1, bar: 4 });
    });

    test("lookup and definition", () => {
        expect(evaluateExpr("{'a': 1}['a']")).toBe(1);
        expect(evaluateExpr("{1: 2}[1]")).toBe(2);
    });

    test("can get values with get method", () => {
        expect(evaluateExpr("{'a': 1}.get('a')")).toBe(1);
        expect(evaluateExpr("{'a': 1}.get('b')")).toBe(null);
        expect(evaluateExpr("{'a': 1}.get('b', 54)")).toBe(54);
    });

    test("can get values from values 'context'", () => {
        expect(evaluateExpr("context.get('a')", { context: { a: 123 } })).toBe(123);
        const values = { context: { a: { b: { c: 321 } } } };
        expect(evaluateExpr("context.get('a').b.c", values)).toBe(321);
        expect(evaluateExpr("context.get('a', {'e': 5}).b.c", values)).toBe(321);
        expect(evaluateExpr("context.get('d', 3)", values)).toBe(3);
        expect(evaluateExpr("context.get('d', {'e': 5})['e']", values)).toBe(5);
    });

    test("can check if a key is in the 'context'", () => {
        expect(evaluateExpr("'a' in context", { context: { a: 123 } })).toBe(true);
        expect(evaluateExpr("'a' in context", { context: { b: 123 } })).toBe(false);
        expect(evaluateExpr("'a' not in context", { context: { a: 123 } })).toBe(false);
        expect(evaluateExpr("'a' not in context", { context: { b: 123 } })).toBe(true);
    });
});

describe("objects", () => {
    test("can read values from object", () => {
        expect(evaluateExpr("obj.a", { obj: { a: 123 } })).toBe(123);
        expect(evaluateExpr("obj.a.b.c", { obj: { a: { b: { c: 321 } } } })).toBe(321);
    });

    test("cannot call function in object", () => {
        expect(() => evaluateExpr("obj.f(3)", { obj: { f: (n) => n + 1 } })).toThrow();
    });
});

describe("if expressions", () => {
    test("simple if expressions", () => {
        expect(evaluateExpr("1 if True else 2")).toBe(1);
        expect(evaluateExpr("1 if 3 < 2 else 'greater'")).toBe("greater");
    });

    test("only evaluate proper branch", () => {
        // will throw if evaluate wrong branch => name error
        expect(evaluateExpr("1 if True else boom")).toBe(1);
        expect(evaluateExpr("boom if False else 222")).toBe(222);
    });
});

describe("miscellaneous expressions", () => {
    test("tuple in list", () => {
        expect(evaluateExpr("[(1 + 2,'foo', True)]")).toEqual([[3, "foo", true]]);
    });
});

describe("evaluate to boolean", () => {
    test("simple expression", () => {
        expect(evaluateBooleanExpr("12")).toBe(true);
        expect(evaluateBooleanExpr("0")).toBe(false);
        expect(evaluateBooleanExpr("0 + 3 - 1")).toBe(true);
        expect(evaluateBooleanExpr("0 + 3 - 1 - 2")).toBe(false);
        expect(evaluateBooleanExpr('"foo"')).toBe(true);
        expect(evaluateBooleanExpr("[1]")).toBe(true);
        expect(evaluateBooleanExpr("[]")).toBe(false);
    });

    test("use contextual values", () => {
        expect(evaluateBooleanExpr("a", { a: 12 })).toBe(true);
        expect(evaluateBooleanExpr("a", { a: 0 })).toBe(false);
        expect(evaluateBooleanExpr("0 + 3 - a", { a: 1 })).toBe(true);
        expect(evaluateBooleanExpr("0 + 3 - a - 2", { a: 1 })).toBe(false);
        expect(evaluateBooleanExpr("0 + 3 - a - b", { a: 1, b: 2 })).toBe(false);
        expect(evaluateBooleanExpr("a", { a: "foo" })).toBe(true);
        expect(evaluateBooleanExpr("a", { a: [1] })).toBe(true);
        expect(evaluateBooleanExpr("a", { a: [] })).toBe(false);
    });

    test("throw if has missing value", () => {
        expect(() => evaluateBooleanExpr("a", { b: 0 })).toThrow();
        expect(evaluateBooleanExpr("1 or a")).toBe(true); // do not throw (lazy value)
        expect(() => evaluateBooleanExpr("0 or a")).toThrow();
        expect(() => evaluateBooleanExpr("a or b", { b: true })).toThrow();
        expect(() => evaluateBooleanExpr("a and b", { b: true })).toThrow();
        expect(() => evaluateBooleanExpr("a()")).toThrow();
        expect(() => evaluateBooleanExpr("a[0]")).toThrow();
        expect(() => evaluateBooleanExpr("a.b")).toThrow();
        expect(() => evaluateBooleanExpr("0 + 3 - a", { b: 1 })).toThrow();
        expect(() => evaluateBooleanExpr("0 + 3 - a - 2", { b: 1 })).toThrow();
        expect(() => evaluateBooleanExpr("0 + 3 - a - b", { b: 2 })).toThrow();
    });
});

describe("sets", () => {
    test("static set", () => {
        expect(evaluateExpr("set()")).toEqual(new Set());
        expect(evaluateExpr("set([])")).toEqual(new Set([]));
        expect(evaluateExpr("set([0])")).toEqual(new Set([0]));
        expect(evaluateExpr("set([1])")).toEqual(new Set([1]));
        expect(evaluateExpr("set([0, 0])")).toEqual(new Set([0]));
        expect(evaluateExpr("set([0, 1])")).toEqual(new Set([0, 1]));
        expect(evaluateExpr("set([1, 1])")).toEqual(new Set([1]));

        expect(evaluateExpr("set('')")).toEqual(new Set());
        expect(evaluateExpr("set('a')")).toEqual(new Set(["a"]));
        expect(evaluateExpr("set('ab')")).toEqual(new Set(["a", "b"]));

        expect(evaluateExpr("set({})")).toEqual(new Set());
        expect(evaluateExpr("set({ 'a': 1 })")).toEqual(new Set(["a"]));
        expect(evaluateExpr("set({ '': 1, 'a': 1 })")).toEqual(new Set(["", "a"]));

        expect(() => evaluateExpr("set(0)")).toThrow();
        expect(() => evaluateExpr("set(1)")).toThrow();
        expect(() => evaluateExpr("set(None)")).toThrow();
        expect(() => evaluateExpr("set(false)")).toThrow();
        expect(() => evaluateExpr("set(true)")).toThrow();
        expect(() => evaluateExpr("set(1, 2)")).toThrow();

        expect(() => evaluateExpr("set(expr)", { expr: undefined })).toThrow();
        expect(() => evaluateExpr("set(expr)", { expr: null })).toThrow();

        expect(() => evaluateExpr("set([], [])")).toThrow(); // valid but not supported by py_js
        expect(() => evaluateExpr("set({ 'a' })")).toThrow(); // valid but not supported by py_js
    });

    test("set intersection", () => {
        expect(evaluateExpr("set([1,2,3]).intersection()")).toEqual(new Set([1, 2, 3]));
        expect(evaluateExpr("set([1,2,3]).intersection(set([2,3]))")).toEqual(new Set([2, 3]));
        expect(evaluateExpr("set([1,2,3]).intersection([2,3])")).toEqual(new Set([2, 3]));
        expect(evaluateExpr("set([1,2,3]).intersection(r)", { r: [2, 3] })).toEqual(
            new Set([2, 3])
        );
        expect(evaluateExpr("r.intersection([2,3])", { r: new Set([1, 2, 3, 2]) })).toEqual(
            new Set([2, 3])
        );

        expect(evaluateExpr("set(foo_ids).intersection([2,3])", { foo_ids: [1, 2] })).toEqual(
            new Set([2])
        );
        expect(evaluateExpr("set(foo_ids).intersection([2,3])", { foo_ids: [1] })).toEqual(
            new Set()
        );
        expect(evaluateExpr("set([foo_id]).intersection([2,3])", { foo_id: 1 })).toEqual(new Set());
        expect(evaluateExpr("set([foo_id]).intersection([2,3])", { foo_id: 2 })).toEqual(
            new Set([2])
        );

        expect(() => evaluateExpr("set([]).intersection([], [])")).toThrow(); // valid but not supported by py_js
        expect(() => evaluateExpr("set([]).intersection([], [], [])")).toThrow(); // valid but not supported by py_js
    });

    test("set difference", () => {
        expect(evaluateExpr("set([1,2,3]).difference()")).toEqual(new Set([1, 2, 3]));
        expect(evaluateExpr("set([1,2,3]).difference(set([2,3]))")).toEqual(new Set([1]));
        expect(evaluateExpr("set([1,2,3]).difference([2,3])")).toEqual(new Set([1]));
        expect(evaluateExpr("set([1,2,3]).difference(r)", { r: [2, 3] })).toEqual(new Set([1]));
        expect(evaluateExpr("r.difference([2,3])", { r: new Set([1, 2, 3, 2, 4]) })).toEqual(
            new Set([1, 4])
        );

        expect(evaluateExpr("set(foo_ids).difference([2,3])", { foo_ids: [1, 2] })).toEqual(
            new Set([1])
        );
        expect(evaluateExpr("set(foo_ids).difference([2,3])", { foo_ids: [1] })).toEqual(
            new Set([1])
        );
        expect(evaluateExpr("set([foo_id]).difference([2,3])", { foo_id: 1 })).toEqual(
            new Set([1])
        );
        expect(evaluateExpr("set([foo_id]).difference([2,3])", { foo_id: 2 })).toEqual(new Set());

        expect(() => evaluateExpr("set([]).difference([], [])")).toThrow(); // valid but not supported by py_js
        expect(() => evaluateExpr("set([]).difference([], [], [])")).toThrow(); // valid but not supported by py_js
    });

    test("set union", () => {
        expect(evaluateExpr("set([1,2,3]).union()")).toEqual(new Set([1, 2, 3]));
        expect(evaluateExpr("set([1,2,3]).union(set([2,3,4]))")).toEqual(new Set([1, 2, 3, 4]));
        expect(evaluateExpr("set([1,2,3]).union([2,4])")).toEqual(new Set([1, 2, 3, 4]));
        expect(evaluateExpr("set([1,2,3]).union(r)", { r: [2, 4] })).toEqual(new Set([1, 2, 3, 4]));
        expect(evaluateExpr("r.union([2,3])", { r: new Set([1, 2, 2, 4]) })).toEqual(
            new Set([1, 2, 4, 3])
        );

        expect(evaluateExpr("set(foo_ids).union([2,3])", { foo_ids: [1, 2] })).toEqual(
            new Set([1, 2, 3])
        );
        expect(evaluateExpr("set(foo_ids).union([2,3])", { foo_ids: [1] })).toEqual(
            new Set([1, 2, 3])
        );
        expect(evaluateExpr("set([foo_id]).union([2,3])", { foo_id: 1 })).toEqual(
            new Set([1, 2, 3])
        );
        expect(evaluateExpr("set([foo_id]).union([2,3])", { foo_id: 2 })).toEqual(new Set([2, 3]));

        expect(() => evaluateExpr("set([]).union([], [])")).toThrow(); // valid but not supported by py_js
        expect(() => evaluateExpr("set([]).union([], [], [])")).toThrow(); // valid but not supported by py_js
    });
});
