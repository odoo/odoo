import { describe, expect, test } from "@odoo/hoot";

import { evaluateExpr, formatAST, parseExpr } from "@web/core/py_js/py";
import { PyDate, PyDateTime } from "@web/core/py_js/py_date";
import { toPyValue } from "@web/core/py_js/py_utils";

const checkAST = (expr, message = expr) => {
    const ast = parseExpr(expr);
    const str = formatAST(ast);
    if (str !== expr) {
        throw new Error(`mismatch: ${str} !== ${expr} (${message});`);
    }
    return true;
};

describe.current.tags("headless");

describe("formatAST", () => {
    test("basic values", () => {
        expect(checkAST("1", "number value")).toBe(true);
        expect(checkAST("1.4", "float value")).toBe(true);
        expect(checkAST("-12", "negative number value")).toBe(true);
        expect(checkAST("True", "boolean")).toBe(true);
        expect(checkAST(`"some string"`, "a string")).toBe(true);
        expect(checkAST("None", "None")).toBe(true);
    });

    test("dictionary", () => {
        expect(checkAST("{}", "empty dictionary")).toBe(true);
        expect(checkAST(`{"a": 1}`, "dictionary with a single key")).toBe(true);
        expect(checkAST(`d["a"]`, "get a value in a dictionary")).toBe(true);
    });

    test("list", () => {
        expect(checkAST("[]", "empty list")).toBe(true);
        expect(checkAST("[1]", "list with one value")).toBe(true);
        expect(checkAST("[1, 2]", "list with two values")).toBe(true);
    });

    test("tuple", () => {
        expect(checkAST("()", "empty tuple")).toBe(true);
        expect(checkAST("(1, 2)", "basic tuple")).toBe(true);
    });

    test("simple arithmetic", () => {
        expect(checkAST("1 + 2", "addition")).toBe(true);
        expect(checkAST("+(1 + 2)", "other addition, prefix")).toBe(true);
        expect(checkAST("1 - 2", "substraction")).toBe(true);
        expect(checkAST("-1 - 2", "other substraction")).toBe(true);
        expect(checkAST("-(1 + 2)", "other substraction")).toBe(true);
        expect(checkAST("1 + 2 + 3", "addition of 3 integers")).toBe(true);
        expect(checkAST("a + b", "addition of two variables")).toBe(true);
        expect(checkAST("42 % 5", "modulo operator")).toBe(true);
        expect(checkAST("a * 10", "multiplication")).toBe(true);
        expect(checkAST("a ** 10", "**")).toBe(true);
        expect(checkAST("~10", "bitwise not")).toBe(true);
        expect(checkAST("~(10 + 3)", "bitwise not")).toBe(true);
        expect(checkAST("a * (1 + 2)", "multiplication and addition")).toBe(true);
        expect(checkAST("(a + b) * 43", "addition and multiplication")).toBe(true);
        expect(checkAST("a // 10", "number division")).toBe(true);
    });

    test("boolean operators", () => {
        expect(checkAST("True and False", "boolean operator")).toBe(true);
        expect(checkAST("True or False", "boolean operator or")).toBe(true);
        expect(checkAST("(True or False) and False", "boolean operators and and or")).toBe(true);
        expect(checkAST("not False", "not prefix")).toBe(true);
        expect(checkAST("not foo", "not prefix with variable")).toBe(true);
        expect(checkAST("not a in b", "not prefix with expression")).toBe(true);
    });

    test("conditional expression", () => {
        expect(checkAST("1 if a else 2")).toBe(true);
        expect(checkAST("[] if a else 2")).toBe(true);
    });

    test("other operators", () => {
        expect(checkAST("x == y", "== operator")).toBe(true);
        expect(checkAST("x != y", "!= operator")).toBe(true);
        expect(checkAST("x < y", "< operator")).toBe(true);
        expect(checkAST("x is y", "is operator")).toBe(true);
        expect(checkAST("x is not y", "is and not operator")).toBe(true);
        expect(checkAST("x in y", "in operator")).toBe(true);
        expect(checkAST("x not in y", "not in operator")).toBe(true);
    });

    test("equality", () => {
        expect(checkAST("a == b", "simple equality")).toBe(true);
    });

    test("strftime", () => {
        expect(checkAST(`time.strftime("%Y")`, "strftime with year")).toBe(true);
        expect(checkAST(`time.strftime("%Y") + "-01-30"`, "strftime with year")).toBe(true);
        expect(checkAST(`time.strftime("%Y-%m-%d %H:%M:%S")`, "strftime with year")).toBe(true);
    });

    test("context_today", () => {
        expect(checkAST(`context_today().strftime("%Y-%m-%d")`, "context today call")).toBe(true);
    });

    test("function call", () => {
        expect(checkAST("td()", "simple call")).toBe(true);
        expect(checkAST("td(a, b, c)", "simple call with args")).toBe(true);
        expect(checkAST("td(days = 1)", "simple call with kwargs")).toBe(true);
        expect(checkAST("f(1, 2, days = 1)", "mixing args and kwargs")).toBe(true);
        expect(checkAST("str(td(2))", "function call in function call")).toBe(true);
    });

    test("various expressions", () => {
        expect(checkAST("(a - b).days", "substraction and .days")).toBe(true);
        expect(checkAST("a + day == date(2002, 3, 3)")).toBe(true);
        const expr = `[("type", "=", "in"), ("day", "<=", time.strftime("%Y-%m-%d")), ("day", ">", (context_today() - datetime.timedelta(days = 15)).strftime("%Y-%m-%d"))]`;
        expect(checkAST(expr)).toBe(true);
    });

    test("escaping support", () => {
        expect(evaluateExpr(String.raw`"\x61"`)).toBe("a", { message: "hex escapes" });
        expect(evaluateExpr(String.raw`"\\abc"`)).toBe(String.raw`\abc`, {
            message: "escaped backslash",
        });
        expect(checkAST(String.raw`"\\abc"`, "escaped backslash AST check")).toBe(true);
        const a = String.raw`'foo\\abc"\''`;
        const b = formatAST(parseExpr(formatAST(parseExpr(a))));
        // Our repr uses JSON.stringify which always uses double quotes,
        // whereas Python's repr is single-quote-biased: strings are repr'd
        // using single quote delimiters *unless* they contain single quotes and
        // no double quotes, then they're delimited with double quotes.
        expect(b).toBe(String.raw`"foo\\abc\"'"`);
    });

    test("null value", () => {
        expect(formatAST(toPyValue(null))).toBe("None");
    });
});

describe("toPyValue", () => {
    test("toPyValue a string", () => {
        const ast = toPyValue("test");
        expect(ast.type).toBe(1);
        expect(ast.value).toBe("test");
        expect(formatAST(ast)).toBe('"test"');
    });

    test("toPyValue a number", () => {
        const ast = toPyValue(1);
        expect(ast.type).toBe(0);
        expect(ast.value).toBe(1);
        expect(formatAST(ast)).toBe("1");
    });

    test("toPyValue a boolean", () => {
        let ast = toPyValue(true);
        expect(ast.type).toBe(2);
        expect(ast.value).toBe(true);
        expect(formatAST(ast)).toBe("True");

        ast = toPyValue(false);
        expect(ast.type).toBe(2);
        expect(ast.value).toBe(false);
        expect(formatAST(ast)).toBe("False");
    });

    test("toPyValue a object", () => {
        const ast = toPyValue({ a: 1 });
        expect(ast.type).toBe(11);
        expect("a" in ast.value).toBe(true);
        expect(["type", "value"].every((prop) => prop in ast.value.a)).toBe(true);
        expect(ast.value.a.type).toBe(0);
        expect(ast.value.a.value).toBe(1);
        expect(formatAST(ast)).toBe('{"a": 1}');
    });

    test("toPyValue a date", () => {
        const date = new Date(Date.UTC(2000, 0, 1));
        const ast = toPyValue(date);
        expect(ast.type).toBe(1);
        const expectedValue = PyDateTime.convertDate(date);
        expect(ast.value.isEqual(expectedValue)).toBe(true);
        expect(formatAST(ast)).toBe(JSON.stringify(expectedValue));
    });

    test("toPyValue a dateime", () => {
        const datetime = new Date(Date.UTC(2000, 0, 1, 1, 0, 0, 0));
        const ast = toPyValue(datetime);
        expect(ast.type).toBe(1);
        const expectedValue = PyDateTime.convertDate(datetime);
        expect(ast.value.isEqual(expectedValue)).toBe(true);
        expect(formatAST(ast)).toBe(JSON.stringify(expectedValue));
    });

    test("toPyValue a PyDate", () => {
        const value = new PyDate(2000, 1, 1);
        const ast = toPyValue(value);
        expect(ast.type).toBe(1);
        expect(ast.value).toBe(value);
        expect(formatAST(ast)).toBe(JSON.stringify(value));
    });

    test("toPyValue a PyDateTime", () => {
        const value = new PyDateTime(2000, 1, 1, 1, 0, 0, 0);
        const ast = toPyValue(value);
        expect(ast.type).toBe(1);
        expect(ast.value).toBe(value);
        expect(formatAST(ast)).toBe(JSON.stringify(value));
    });
});
