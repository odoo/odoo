/** @odoo-module **/

import { tokenize } from "@web/core/py_js/py";

QUnit.module("py", {}, () => {
    QUnit.module("tokenizer");

    QUnit.test("can tokenize simple expressions with spaces", (assert) => {
        assert.deepEqual(tokenize("1"), [{ type: 0 /* Number */, value: 1 }]);
        assert.deepEqual(tokenize(" 1"), [{ type: 0 /* Number */, value: 1 }]);
        assert.deepEqual(tokenize(" 1 "), [{ type: 0 /* Number */, value: 1 }]);
    });

    QUnit.test("can tokenize numbers", (assert) => {
        /* Without exponent */
        assert.deepEqual(tokenize("1"), [{ type: 0 /* Number */, value: 1 }]);
        assert.deepEqual(tokenize("13"), [{ type: 0 /* Number */, value: 13 }]);
        assert.deepEqual(tokenize("-1"), [
            { type: 2 /* Symbol */, value: "-" },
            { type: 0 /* Number */, value: 1 },
        ]);

        /* With exponent */
        assert.deepEqual(tokenize("1e2"), [{ type: 0 /* Number */, value: 100 }]);
        assert.deepEqual(tokenize("13E+02"), [{ type: 0 /* Number */, value: 1300 }]);
        assert.deepEqual(tokenize("15E-2"), [{ type: 0 /* Number */, value: 0.15 }]);
        assert.deepEqual(tokenize("-30e+002"), [
            { type: 2 /* Symbol */, value: "-" },
            { type: 0 /* Number */, value: 3000 },
        ]);
    });

    QUnit.test("can tokenize floats", (assert) => {
        /* Without exponent */
        assert.deepEqual(tokenize("12.0"), [{ type: 0 /* Number */, value: 12 }]);
        assert.deepEqual(tokenize("1.2"), [{ type: 0 /* Number */, value: 1.2 }]);
        assert.deepEqual(tokenize(".42"), [{ type: 0 /* Number */, value: 0.42 }]);
        assert.deepEqual(tokenize("12."), [{type: 0 /* Number */, value: 12}]);
        assert.deepEqual(tokenize("-1.23"), [
            { type: 2 /* Symbol */, value: "-" },
            { type: 0 /* Number */, value: 1.23 },
        ]);

        /* With exponent */
        assert.deepEqual(tokenize("1234e-3"), [{type: 0 /* Number */, value: 1.234}]);
        assert.deepEqual(tokenize("1.23E-03"), [{type: 0 /* Number */, value: 0.00123}]);
        assert.deepEqual(tokenize('.23e-3'), [{type: 0 /* Number */, value: 0.00023}]);
        assert.deepEqual(tokenize('23.e-03'), [{type: 0 /* Number */, value: 0.023}]);

        assert.deepEqual(tokenize("12.1E2"), [{type: 0 /* Number */, value: 1210}]);
        assert.deepEqual(tokenize("1.23e+03"), [{type: 0 /* Number */, value: 1230}]);
        assert.deepEqual(tokenize('.23e2'), [{type: 0 /* Number */, value: 23}]);
        assert.deepEqual(tokenize('15.E+02'), [{type: 0 /* Number */, value: 1500}]);

        assert.deepEqual(tokenize("-23E02"), [
            {type: 2 /* Symbol */, value: "-"},
            {type: 0 /* Number */, value: 2300}
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
});
