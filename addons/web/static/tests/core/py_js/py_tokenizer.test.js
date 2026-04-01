import { describe, expect, test } from "@odoo/hoot";

import { tokenize } from "@web/core/py_js/py";

describe.current.tags("headless");

test("can tokenize simple expressions with spaces", () => {
    expect(tokenize("1")).toEqual([{ type: 0 /* Number */, value: 1 }]);
    expect(tokenize(" 1")).toEqual([{ type: 0 /* Number */, value: 1 }]);
    expect(tokenize(" 1 ")).toEqual([{ type: 0 /* Number */, value: 1 }]);
});

test("can tokenize numbers", () => {
    /* Without exponent */
    expect(tokenize("1")).toEqual([{ type: 0 /* Number */, value: 1 }]);
    expect(tokenize("13")).toEqual([{ type: 0 /* Number */, value: 13 }]);
    expect(tokenize("-1")).toEqual([
        { type: 2 /* Symbol */, value: "-" },
        { type: 0 /* Number */, value: 1 },
    ]);

    /* With exponent */
    expect(tokenize("1e2")).toEqual([{ type: 0 /* Number */, value: 100 }]);
    expect(tokenize("13E+02")).toEqual([{ type: 0 /* Number */, value: 1300 }]);
    expect(tokenize("15E-2")).toEqual([{ type: 0 /* Number */, value: 0.15 }]);
    expect(tokenize("-30e+002")).toEqual([
        { type: 2 /* Symbol */, value: "-" },
        { type: 0 /* Number */, value: 3000 },
    ]);
});

test("can tokenize floats", () => {
    /* Without exponent */
    expect(tokenize("12.0")).toEqual([{ type: 0 /* Number */, value: 12 }]);
    expect(tokenize("1.2")).toEqual([{ type: 0 /* Number */, value: 1.2 }]);
    expect(tokenize(".42")).toEqual([{ type: 0 /* Number */, value: 0.42 }]);
    expect(tokenize("12.")).toEqual([{ type: 0 /* Number */, value: 12 }]);
    expect(tokenize("-1.23")).toEqual([
        { type: 2 /* Symbol */, value: "-" },
        { type: 0 /* Number */, value: 1.23 },
    ]);

    /* With exponent */
    expect(tokenize("1234e-3")).toEqual([{ type: 0 /* Number */, value: 1.234 }]);
    expect(tokenize("1.23E-03")).toEqual([{ type: 0 /* Number */, value: 0.00123 }]);
    expect(tokenize(".23e-3")).toEqual([{ type: 0 /* Number */, value: 0.00023 }]);
    expect(tokenize("23.e-03")).toEqual([{ type: 0 /* Number */, value: 0.023 }]);

    expect(tokenize("12.1E2")).toEqual([{ type: 0 /* Number */, value: 1210 }]);
    expect(tokenize("1.23e+03")).toEqual([{ type: 0 /* Number */, value: 1230 }]);
    expect(tokenize(".23e2")).toEqual([{ type: 0 /* Number */, value: 23 }]);
    expect(tokenize("15.E+02")).toEqual([{ type: 0 /* Number */, value: 1500 }]);

    expect(tokenize("-23E02")).toEqual([
        { type: 2 /* Symbol */, value: "-" },
        { type: 0 /* Number */, value: 2300 },
    ]);
});

test("can tokenize strings", () => {
    expect(tokenize('"foo"')).toEqual([{ type: 1 /* String */, value: "foo" }]);
});

test("can tokenize bare names", () => {
    expect(tokenize("foo")).toEqual([{ type: 3 /* Name */, value: "foo" }]);
});

test("can tokenize misc operators", () => {
    expect(tokenize("in")).toEqual([{ type: 2 /* Symbol */, value: "in" }]);
    expect(tokenize("not in")).toEqual([{ type: 2 /* Symbol */, value: "not in" }]);
    expect(tokenize("3 ** 2")[1]).toEqual({ type: 2 /* Symbol */, value: "**" });
});

test("can tokenize constants", () => {
    expect(tokenize("None")).toEqual([{ type: 4 /* Constant */, value: "None" }]);
    expect(tokenize("True")).toEqual([{ type: 4 /* Constant */, value: "True" }]);
    expect(tokenize("False")).toEqual([{ type: 4 /* Constant */, value: "False" }]);
});

test("can tokenize parenthesis", () => {
    expect(tokenize("()")).toEqual([
        { type: 2 /* Symbol */, value: "(" },
        { type: 2 /* Symbol */, value: ")" },
    ]);
});

test("can tokenize function with kwargs", () => {
    expect(tokenize('foo(bar=3, qux="4")')).toEqual([
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

test("can tokenize if statement", () => {
    expect(tokenize("1 if True else 2")).toEqual([
        { type: 0 /* Number */, value: 1 },
        { type: 2 /* Symbol */, value: "if" },
        { type: 4 /* Constant */, value: "True" },
        { type: 2 /* Symbol */, value: "else" },
        { type: 0 /* Number */, value: 2 },
    ]);
});

test("sanity check: throw some errors", () => {
    expect(() => tokenize("'asdf")).toThrow();
});
