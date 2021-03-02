/** @odoo-module **/
import { formatAST, evaluateExpr, parseExpr, tokenize } from "../../src/py_js/index";
import { toPyDict } from "../../src/py_js/utils";

QUnit.module("py", {}, () => {
  QUnit.module("tokenizer");
  QUnit.test("can tokenize simple expressions with spaces", (assert) => {
    assert.deepEqual(tokenize("1"), [{ type: 0 /* Number */, value: 1 }]);
    assert.deepEqual(tokenize(" 1"), [{ type: 0 /* Number */, value: 1 }]);
    assert.deepEqual(tokenize(" 1 "), [{ type: 0 /* Number */, value: 1 }]);
  });
  QUnit.test("can tokenize numbers", (assert) => {
    assert.deepEqual(tokenize("1"), [{ type: 0 /* Number */, value: 1 }]);
    assert.deepEqual(tokenize("13"), [{ type: 0 /* Number */, value: 13 }]);
    assert.deepEqual(tokenize("12.0"), [{ type: 0 /* Number */, value: 12 }]);
    assert.deepEqual(tokenize("1.2"), [{ type: 0 /* Number */, value: 1.2 }]);
    assert.deepEqual(tokenize("1.2"), [{ type: 0 /* Number */, value: 1.2 }]);
    assert.deepEqual(tokenize(".42"), [{ type: 0 /* Number */, value: 0.42 }]);
    assert.deepEqual(tokenize("-1"), [
      { type: 2 /* Symbol */, value: "-" },
      { type: 0 /* Number */, value: 1 },
    ]);
  });
  QUnit.test("can tokenize strings", (assert) => {
    assert.deepEqual(tokenize('"foo"'), [{ type: 1 /* String */, value: "foo" }]);
  });
  QUnit.test("can tokenize bare names", (assert) => {
    assert.deepEqual(tokenize("foo"), [{ type: 3 /* Name */, value: "foo" }]);
  });
  QUnit.test("can tokenize misc operators", (assert) => {
    assert.deepEqual(tokenize("in"), [{ type: 2 /* Symbol */, value: "in" }]);
    assert.deepEqual(tokenize("not in"), [{ type: 2 /* Symbol */, value: "not in" }]);
    assert.deepEqual(tokenize("3 ** 2")[1], { type: 2 /* Symbol */, value: "**" });
  });
  QUnit.test("can tokenize constants", (assert) => {
    assert.deepEqual(tokenize("None"), [{ type: 4 /* Constant */, value: "None" }]);
    assert.deepEqual(tokenize("True"), [{ type: 4 /* Constant */, value: "True" }]);
    assert.deepEqual(tokenize("False"), [{ type: 4 /* Constant */, value: "False" }]);
  });
  QUnit.test("can tokenize parenthesis", (assert) => {
    assert.deepEqual(tokenize("()"), [
      { type: 2 /* Symbol */, value: "(" },
      { type: 2 /* Symbol */, value: ")" },
    ]);
  });
  QUnit.test("can tokenize function with kwargs", (assert) => {
    assert.deepEqual(tokenize('foo(bar=3, qux="4")'), [
      { type: 3 /* Name */, value: "foo" },
      { type: 2 /* Symbol */, value: "(" },
      { type: 3 /* Name */, value: "bar" },
      { type: 2 /* Symbol */, value: "=" },
      { type: 0 /* Number */, value: 3 },
      { type: 2 /* Symbol */, value: "," },
      { type: 3 /* Name */, value: "qux" },
      { type: 2 /* Symbol */, value: "=" },
      { type: 1 /* String */, value: "4" },
      { type: 2 /* Symbol */, value: ")" },
    ]);
  });
  QUnit.test("can tokenize if statement", (assert) => {
    assert.deepEqual(tokenize("1 if True else 2"), [
      { type: 0 /* Number */, value: 1 },
      { type: 2 /* Symbol */, value: "if" },
      { type: 4 /* Constant */, value: "True" },
      { type: 2 /* Symbol */, value: "else" },
      { type: 0 /* Number */, value: 2 },
    ]);
  });
  QUnit.test("sanity check: throw some errors", (assert) => {
    assert.throws(() => tokenize("'asdf"));
  });
  QUnit.module("parser");
  QUnit.test("can parse basic elements", (assert) => {
    assert.deepEqual(parseExpr("1"), { type: 0 /* Number */, value: 1 });
    assert.deepEqual(parseExpr('"foo"'), { type: 1 /* String */, value: "foo" });
    assert.deepEqual(parseExpr("foo"), { type: 5 /* Name */, value: "foo" });
    assert.deepEqual(parseExpr("True"), { type: 2 /* Boolean */, value: true });
    assert.deepEqual(parseExpr("False"), { type: 2 /* Boolean */, value: false });
    assert.deepEqual(parseExpr("None"), { type: 3 /* None */ });
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
  QUnit.module("interpreter", () => {
    QUnit.module("basic values");
    QUnit.test("evaluate simple values", (assert) => {
      assert.strictEqual(evaluateExpr("12"), 12);
      assert.strictEqual(evaluateExpr('"foo"'), "foo");
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
      assert.strictEqual(evaluateExpr("foo == 'foo' and bar == 'bar'", { foo: "bar" }), false);
      assert.strictEqual(evaluateExpr("foo == 'foo' or bar == 'bar'", { foo: "foo" }), true);
    });
    QUnit.test("should return the actual object", (assert) => {
      assert.strictEqual(evaluateExpr('"foo" or "bar"'), "foo");
      assert.strictEqual(evaluateExpr('None or "bar"'), "bar");
      assert.strictEqual(evaluateExpr("False or None"), null);
      assert.strictEqual(evaluateExpr("0 or 1"), 1);
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
    QUnit.test("python values in context", (assert) => {
      const context = toPyDict({ b: 3 });
      assert.strictEqual(evaluateExpr("context.get('b', 54)", { context }), 3);
      assert.strictEqual(evaluateExpr("context.get('c', 54)", { context }), 54);
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
      assert.strictEqual(evaluateExpr("bool('')"), false);
      assert.strictEqual(evaluateExpr("bool('foo')"), true);
      assert.strictEqual(evaluateExpr("bool(date_deadline)", { date_deadline: "2008" }), true);
      assert.strictEqual(evaluateExpr("bool(s)", { s: "" }), false);
    });
    QUnit.module("callables");
    QUnit.test("should call function from context", (assert) => {
      assert.strictEqual(evaluateExpr("foo()", { foo: () => 3 }), 3);
      assert.strictEqual(evaluateExpr("1 + foo()", { foo: () => 3 }), 4);
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
    QUnit.module("objects");
    QUnit.test("can read values from object", (assert) => {
      assert.strictEqual(evaluateExpr("obj.a", { obj: { a: 123 } }), 123);
      assert.strictEqual(evaluateExpr("obj.a.b.c", { obj: { a: { b: { c: 321 } } } }), 321);
    });
    QUnit.test("can call function in object", (assert) => {
      assert.strictEqual(evaluateExpr("obj.f(3)", { obj: { f: (n) => n + 1 } }), 4);
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
  });
  QUnit.module("builtins", () => {
    QUnit.module("time");
    function check(expr, fn) {
      const d0 = new Date();
      const result = evaluateExpr(expr);
      const d1 = new Date();
      return fn(d0) <= result && result <= fn(d1);
    }
    const format = (n) => String(n).padStart(2, "0");
    const formatDate = (d) => {
      const year = d.getUTCFullYear();
      const month = format(d.getUTCMonth() + 1);
      const day = format(d.getUTCDate());
      return `${year}-${month}-${day}`;
    };
    const formatDateTime = (d) => {
      const h = format(d.getUTCHours());
      const m = format(d.getUTCMinutes());
      const s = format(d.getUTCSeconds());
      return `${formatDate(d)} ${h}:${m}:${s}`;
    };
    QUnit.test("strftime", (assert) => {
      assert.ok(check("time.strftime('%Y')", (d) => String(d.getFullYear())));
      assert.ok(check("time.strftime('%Y') + '-01-30'", (d) => String(d.getFullYear()) + "-01-30"));
      assert.ok(check("time.strftime('%Y-%m-%d %H:%M:%S')", formatDateTime));
    });
    QUnit.module("datetime.datetime");
    QUnit.test("datetime.datetime.now", (assert) => {
      console.log(evaluateExpr("datetime.datetime.now().month"));
      assert.ok(check("datetime.datetime.now().year", (d) => d.getUTCFullYear()));
      assert.ok(check("datetime.datetime.now().month", (d) => d.getUTCMonth() + 1));
      assert.ok(check("datetime.datetime.now().day", (d) => d.getUTCDate()));
      assert.ok(check("datetime.datetime.now().hour", (d) => d.getUTCHours()));
      assert.ok(check("datetime.datetime.now().minute", (d) => d.getUTCMinutes()));
      assert.ok(check("datetime.datetime.now().second", (d) => d.getUTCSeconds()));
    });
    QUnit.test("various operations", (assert) => {
      const expr1 = "datetime.datetime(day=3,month=4,year=2001).strftime('%Y-%m-%d')";
      assert.strictEqual(evaluateExpr(expr1), "2001-04-03");
      const expr2 = "datetime.datetime(2001, 4, 3).strftime('%Y-%m-%d')";
      assert.strictEqual(evaluateExpr(expr2), "2001-04-03");
      const expr3 =
        "datetime.datetime(day=3,month=4,second=12, year=2001,minute=32).strftime('%Y-%m-%d %H:%M:%S')";
      assert.strictEqual(evaluateExpr(expr3), "2001-04-03 00:32:12");
    });
    QUnit.test("datetime.datetime.combine", (assert) => {
      const expr =
        "datetime.datetime.combine(context_today(), datetime.time(23,59,59)).strftime('%Y-%m-%d %H:%M:%S')";
      assert.ok(
        check(expr, (d) => {
          return formatDate(d) + " 23:59:59";
        })
      );
    });
    // datetime.datetime.combine(context_today(), datetime.time(23,59,59))
    QUnit.module("datetime.date");
    QUnit.test("datetime.date.today", (assert) => {
      assert.ok(check("(datetime.date.today()).strftime('%Y-%m-%d')", formatDate));
    });
    QUnit.test("various operations", (assert) => {
      const expr1 = "datetime.date(day=3,month=4,year=2001).strftime('%Y-%m-%d')";
      assert.strictEqual(evaluateExpr(expr1), "2001-04-03");
      const expr2 = "datetime.date(2001, 4, 3).strftime('%Y-%m-%d')";
      assert.strictEqual(evaluateExpr(expr2), "2001-04-03");
    });
    QUnit.module("datetime.time");
    QUnit.test("various operations", (assert) => {
      const expr1 = "datetime.time(hour=3,minute=2. second=1).strftime('%H:%M:%S')";
      assert.strictEqual(evaluateExpr(expr1), "03:02:01");
    });
    QUnit.test("attributes", (assert) => {
      const expr1 = "datetime.time(hour=3,minute=2. second=1).hour";
      assert.strictEqual(evaluateExpr(expr1), 3);
      const expr2 = "datetime.time(hour=3,minute=2. second=1).minute";
      assert.strictEqual(evaluateExpr(expr2), 2);
      const expr3 = "datetime.time(hour=3,minute=2. second=1).second";
      assert.strictEqual(evaluateExpr(expr3), 1);
    });
    QUnit.module("relativedelta");
    QUnit.test("adding date and relative delta", (assert) => {
      const expr1 =
        "(datetime.date(day=3,month=4,year=2001) + relativedelta(days=-1)).strftime('%Y-%m-%d')";
      assert.strictEqual(evaluateExpr(expr1), "2001-04-02");
      const expr2 =
        "(datetime.date(day=3,month=4,year=2001) + relativedelta(weeks=-1)).strftime('%Y-%m-%d')";
      assert.strictEqual(evaluateExpr(expr2), "2001-03-27");
    });
    QUnit.test("adding relative delta and date", (assert) => {
      const expr =
        "(relativedelta(days=-1) + datetime.date(day=3,month=4,year=2001)).strftime('%Y-%m-%d')";
      assert.strictEqual(evaluateExpr(expr), "2001-04-02");
    });
    QUnit.module("datetime.timedelta");
    QUnit.test("adding date and time delta", (assert) => {
      const expr =
        "(datetime.date(day=3,month=4,year=2001) + datetime.timedelta(days=-1)).strftime('%Y-%m-%d')";
      assert.strictEqual(evaluateExpr(expr), "2001-04-02");
    });
    QUnit.test("adding time delta and date", (assert) => {
      const expr =
        "(datetime.timedelta(days=-1) + datetime.date(day=3,month=4,year=2001)).strftime('%Y-%m-%d')";
      assert.strictEqual(evaluateExpr(expr), "2001-04-02");
    });
    QUnit.module("misc");
    QUnit.test("context_today", (assert) => {
      assert.ok(check("context_today().strftime('%Y-%m-%d')", formatDate));
    });
    QUnit.test("today", (assert) => {
      assert.ok(check("today", formatDate));
    });
    QUnit.test("now", (assert) => {
      assert.ok(check("now", formatDateTime));
    });
  });
  QUnit.module("formatAST");
  function checkAST(expr, message = expr) {
    const ast = parseExpr(expr);
    const str = formatAST(ast);
    if (str !== expr) {
      throw new Error(`Mismatch: ${str} !== ${expr} (${message});`);
    }
    return true;
  }
  QUnit.test("basic values", function (assert) {
    assert.ok(checkAST("1", "integer value"));
    assert.ok(checkAST("1.4", "float value"));
    assert.ok(checkAST("-12", "negative integer value"));
    assert.ok(checkAST("True", "boolean"));
    assert.ok(checkAST(`"some string"`, "a string"));
    assert.ok(checkAST("None", "None"));
  });
  QUnit.test("dictionary", function (assert) {
    assert.ok(checkAST("{}", "empty dictionary"));
    assert.ok(checkAST(`{"a": 1}`, "dictionary with a single key"));
    assert.ok(checkAST(`d["a"]`, "get a value in a dictionary"));
  });
  QUnit.test("list", function (assert) {
    assert.ok(checkAST("[]", "empty list"));
    assert.ok(checkAST("[1]", "list with one value"));
    assert.ok(checkAST("[1, 2]", "list with two values"));
  });
  QUnit.test("tuple", function (assert) {
    assert.ok(checkAST("()", "empty tuple"));
    assert.ok(checkAST("(1, 2)", "basic tuple"));
  });
  QUnit.test("simple arithmetic", function (assert) {
    assert.ok(checkAST("1 + 2", "addition"));
    assert.ok(checkAST("+(1 + 2)", "other addition, prefix"));
    assert.ok(checkAST("1 - 2", "substraction"));
    assert.ok(checkAST("-1 - 2", "other substraction"));
    assert.ok(checkAST("-(1 + 2)", "other substraction"));
    assert.ok(checkAST("1 + 2 + 3", "addition of 3 integers"));
    assert.ok(checkAST("a + b", "addition of two variables"));
    assert.ok(checkAST("42 % 5", "modulo operator"));
    assert.ok(checkAST("a * 10", "multiplication"));
    assert.ok(checkAST("a ** 10", "**"));
    assert.ok(checkAST("~10", "bitwise not"));
    assert.ok(checkAST("~(10 + 3)", "bitwise not"));
    assert.ok(checkAST("a * (1 + 2)", "multiplication and addition"));
    assert.ok(checkAST("(a + b) * 43", "addition and multiplication"));
    assert.ok(checkAST("a // 10", "integer division"));
  });
  QUnit.test("boolean operators", function (assert) {
    assert.ok(checkAST("True and False", "boolean operator"));
    assert.ok(checkAST("True or False", "boolean operator or"));
    assert.ok(checkAST("(True or False) and False", "boolean operators and and or"));
    assert.ok(checkAST("not False", "not prefix"));
    assert.ok(checkAST("not foo", "not prefix with variable"));
    assert.ok(checkAST("not a in b", "not prefix with expression"));
  });
  QUnit.test("conditional expression", function (assert) {
    assert.ok(checkAST("1 if a else 2"));
    assert.ok(checkAST("[] if a else 2"));
  });
  QUnit.test("other operators", function (assert) {
    assert.ok(checkAST("x == y", "== operator"));
    assert.ok(checkAST("x != y", "!= operator"));
    assert.ok(checkAST("x < y", "< operator"));
    assert.ok(checkAST("x is y", "is operator"));
    assert.ok(checkAST("x is not y", "is and not operator"));
    assert.ok(checkAST("x in y", "in operator"));
    assert.ok(checkAST("x not in y", "not in operator"));
  });
  QUnit.test("equality", function (assert) {
    assert.ok(checkAST("a == b", "simple equality"));
  });
  QUnit.test("strftime", function (assert) {
    assert.ok(checkAST(`time.strftime("%Y")`, "strftime with year"));
    assert.ok(checkAST(`time.strftime("%Y") + "-01-30"`, "strftime with year"));
    assert.ok(checkAST(`time.strftime("%Y-%m-%d %H:%M:%S")`, "strftime with year"));
  });
  QUnit.test("context_today", function (assert) {
    assert.ok(checkAST(`context_today().strftime("%Y-%m-%d")`, "context today call"));
  });
  QUnit.test("function call", function (assert) {
    assert.ok(checkAST("td()", "simple call"));
    assert.ok(checkAST("td(a, b, c)", "simple call with args"));
    assert.ok(checkAST("td(days = 1)", "simple call with kwargs"));
    assert.ok(checkAST("f(1, 2, days = 1)", "mixing args and kwargs"));
    assert.ok(checkAST("str(td(2))", "function call in function call"));
  });
  QUnit.test("various expressions", function (assert) {
    assert.ok(checkAST("(a - b).days", "substraction and .days"));
    assert.ok(checkAST("a + day == date(2002, 3, 3)"));
    const expr = `[("type", "=", "in"), ("day", "<=", time.strftime("%Y-%m-%d")), ("day", ">", (context_today() - datetime.timedelta(days = 15)).strftime("%Y-%m-%d"))]`;
    assert.ok(checkAST(expr));
  });
  QUnit.test("escaping support", function (assert) {
    assert.strictEqual(evaluateExpr(String.raw`"\x61"`), "a", "hex escapes");
    assert.strictEqual(evaluateExpr(String.raw`"\\abc"`), String.raw`\abc`, "escaped backslash");
    assert.ok(checkAST(String.raw`"\\abc"`, "escaped backslash AST check"));
    const a = String.raw`'foo\\abc"\''`;
    const b = formatAST(parseExpr(formatAST(parseExpr(a))));
    // Our repr uses JSON.stringify which always uses double quotes,
    // whereas Python's repr is single-quote-biased: strings are repr'd
    // using single quote delimiters *unless* they contain single quotes and
    // no double quotes, then they're delimited with double quotes.
    assert.strictEqual(b, String.raw`"foo\\abc\"'"`);
  });
});
