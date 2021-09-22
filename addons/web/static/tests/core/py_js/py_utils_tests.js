/** @odoo-module **/

import { evaluateExpr, formatAST, parseExpr } from "@web/core/py_js/py";
import { toPyValue } from "@web/core/py_js/py_utils";

QUnit.module("py", {}, () => {
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
        assert.strictEqual(
            evaluateExpr(String.raw`"\\abc"`),
            String.raw`\abc`,
            "escaped backslash"
        );
        assert.ok(checkAST(String.raw`"\\abc"`, "escaped backslash AST check"));
        const a = String.raw`'foo\\abc"\''`;
        const b = formatAST(parseExpr(formatAST(parseExpr(a))));
        // Our repr uses JSON.stringify which always uses double quotes,
        // whereas Python's repr is single-quote-biased: strings are repr'd
        // using single quote delimiters *unless* they contain single quotes and
        // no double quotes, then they're delimited with double quotes.
        assert.strictEqual(b, String.raw`"foo\\abc\"'"`);
    });

    QUnit.test("null value", function (assert) {
        assert.strictEqual(formatAST(toPyValue(null)), "None");
    });
});
