/** @odoo-module */
import { getFirstPivotFunction, getNumberOfPivotFormulas } from "@spreadsheet/pivot/pivot_helpers";
import { getFirstListFunction, getNumberOfListFormulas } from "@spreadsheet/list/list_helpers";
import { parsePivotFormulaFieldValue } from "@spreadsheet/pivot/pivot_model";

function stringArg(value) {
    return { type: "STRING", value: `${value}` };
}

QUnit.module("spreadsheet > pivot_helpers", {}, () => {
    QUnit.test("Basic formula extractor", async function (assert) {
        const formula = `=ODOO.PIVOT("1", "test") + ODOO.LIST("2", "hello", "bla")`;
        let functionName;
        let args;
        ({ functionName, args } = getFirstPivotFunction(formula));
        assert.strictEqual(functionName, "ODOO.PIVOT");
        assert.strictEqual(args.length, 2);
        assert.deepEqual(args[0], stringArg("1"));
        assert.deepEqual(args[1], stringArg("test"));
        ({ functionName, args } = getFirstListFunction(formula));
        assert.strictEqual(functionName, "ODOO.LIST");
        assert.strictEqual(args.length, 3);
        assert.deepEqual(args[0], stringArg("2"));
        assert.deepEqual(args[1], stringArg("hello"));
        assert.deepEqual(args[2], stringArg("bla"));
    });

    QUnit.test("Extraction with two PIVOT formulas", async function (assert) {
        const formula = `=ODOO.PIVOT("1", "test") + ODOO.PIVOT("2", "hello", "bla")`;
        let functionName;
        let args;
        ({ functionName, args } = getFirstPivotFunction(formula));
        assert.strictEqual(functionName, "ODOO.PIVOT");
        assert.strictEqual(args.length, 2);
        assert.deepEqual(args[0], stringArg("1"));
        assert.deepEqual(args[1], stringArg("test"));
        assert.strictEqual(getFirstListFunction(formula), undefined);
    });

    QUnit.test("Number of formulas", async function (assert) {
        const formula = `=ODOO.PIVOT("1", "test") + ODOO.PIVOT("2", "hello", "bla") + ODOO.LIST("1", "bla")`;
        assert.strictEqual(getNumberOfPivotFormulas(formula), 2);
        assert.strictEqual(getNumberOfListFormulas(formula), 1);
        assert.strictEqual(getNumberOfPivotFormulas("=1+1"), 0);
        assert.strictEqual(getNumberOfListFormulas("=1+1"), 0);
        assert.strictEqual(getNumberOfPivotFormulas("=bla"), 0);
        assert.strictEqual(getNumberOfListFormulas("=bla"), 0);
    });

    QUnit.test("getFirstPivotFunction does not crash when given crap", async function (assert) {
        assert.strictEqual(getFirstListFunction("=SUM(A1)"), undefined);
        assert.strictEqual(getFirstPivotFunction("=SUM(A1)"), undefined);
        assert.strictEqual(getFirstListFunction("=1+1"), undefined);
        assert.strictEqual(getFirstPivotFunction("=1+1"), undefined);
        assert.strictEqual(getFirstListFunction("=bla"), undefined);
        assert.strictEqual(getFirstPivotFunction("=bla"), undefined);
        assert.strictEqual(getFirstListFunction("bla"), undefined);
        assert.strictEqual(getFirstPivotFunction("bla"), undefined);
    });
});

QUnit.module("spreadsheet > parsePivotFormulaFieldValue", {}, () => {
    QUnit.test("parse values of a selection, char or text field", (assert) => {
        for (const fieldType of ["selection", "text", "char"]) {
            const field = {
                type: fieldType,
                string: "A field",
            };
            assert.strictEqual(parsePivotFormulaFieldValue(field, "won"), "won");
            assert.strictEqual(parsePivotFormulaFieldValue(field, "1"), "1");
            assert.strictEqual(parsePivotFormulaFieldValue(field, 1), "1");
            assert.strictEqual(parsePivotFormulaFieldValue(field, "11/2020"), "11/2020");
            assert.strictEqual(parsePivotFormulaFieldValue(field, "2020"), "2020");
            assert.strictEqual(parsePivotFormulaFieldValue(field, "01/11/2020"), "01/11/2020");
            assert.strictEqual(parsePivotFormulaFieldValue(field, "false"), false);
            assert.strictEqual(parsePivotFormulaFieldValue(field, false), false);
            assert.strictEqual(parsePivotFormulaFieldValue(field, "true"), "true");
        }
    });

    QUnit.test("parse values of time fields", (assert) => {
        for (const fieldType of ["date", "datetime"]) {
            const field = {
                type: fieldType,
                string: "A field",
            };
            assert.strictEqual(parsePivotFormulaFieldValue(field, "11/2020"), "11/2020");
            assert.strictEqual(parsePivotFormulaFieldValue(field, "2020"), "2020");
            assert.strictEqual(parsePivotFormulaFieldValue(field, "01/11/2020"), "01/11/2020");
            assert.strictEqual(parsePivotFormulaFieldValue(field, "1"), "1");
            assert.strictEqual(parsePivotFormulaFieldValue(field, 1), "1");
            assert.strictEqual(parsePivotFormulaFieldValue(field, "false"), false);
            assert.strictEqual(parsePivotFormulaFieldValue(field, false), false);
            assert.strictEqual(parsePivotFormulaFieldValue(field, "true"), "true"); // this should throw because it's not a valid date
            assert.strictEqual(parsePivotFormulaFieldValue(field, true), "true"); // this should throw because it's not a valid date
            assert.strictEqual(parsePivotFormulaFieldValue(field, "won"), "won"); // this should throw because it's not a valid date
        }
    });

    QUnit.test("parse values of boolean field", (assert) => {
        const field = {
            type: "boolean",
            string: "A field",
        };
        assert.strictEqual(parsePivotFormulaFieldValue(field, "false"), false);
        assert.strictEqual(parsePivotFormulaFieldValue(field, false), false);
        assert.strictEqual(parsePivotFormulaFieldValue(field, "true"), true);
        assert.strictEqual(parsePivotFormulaFieldValue(field, true), true);
        assert.throws(() => parsePivotFormulaFieldValue(field, "11/2020"));
        assert.throws(() => parsePivotFormulaFieldValue(field, "2020"));
        assert.throws(() => parsePivotFormulaFieldValue(field, "01/11/2020"));
        assert.throws(() => parsePivotFormulaFieldValue(field, "1"));
        assert.throws(() => parsePivotFormulaFieldValue(field, 1));
        assert.throws(() => parsePivotFormulaFieldValue(field, "won"));
    });

    QUnit.test("parse values of numeric fields", (assert) => {
        for (const fieldType of ["float", "integer", "monetary", "many2one", "many2many"]) {
            const field = {
                type: fieldType,
                string: "A field",
            };
            assert.strictEqual(parsePivotFormulaFieldValue(field, "2020"), 2020);
            assert.strictEqual(parsePivotFormulaFieldValue(field, "01/11/2020"), 43841); // a date is actually a number in a spreadsheet
            assert.strictEqual(parsePivotFormulaFieldValue(field, "1"), 1);
            assert.strictEqual(parsePivotFormulaFieldValue(field, 1), 1);
            assert.strictEqual(parsePivotFormulaFieldValue(field, "false"), false);
            assert.strictEqual(parsePivotFormulaFieldValue(field, false), false);
            assert.throws(() => parsePivotFormulaFieldValue(field, "true"));
            assert.throws(() => parsePivotFormulaFieldValue(field, true));
            assert.throws(() => parsePivotFormulaFieldValue(field, "won"));
            assert.throws(() => parsePivotFormulaFieldValue(field, "11/2020"));
        }
    });

    QUnit.test("parse values of unsupported fields", (assert) => {
        for (const fieldType of ["one2many", "binary", "html"]) {
            const field = {
                type: fieldType,
                string: "A field",
            };
            assert.throws(() => parsePivotFormulaFieldValue(field, "false"));
            assert.throws(() => parsePivotFormulaFieldValue(field, false));
            assert.throws(() => parsePivotFormulaFieldValue(field, "true"));
            assert.throws(() => parsePivotFormulaFieldValue(field, true));
            assert.throws(() => parsePivotFormulaFieldValue(field, "11/2020"));
            assert.throws(() => parsePivotFormulaFieldValue(field, "2020"));
            assert.throws(() => parsePivotFormulaFieldValue(field, "01/11/2020"));
            assert.throws(() => parsePivotFormulaFieldValue(field, "1"));
            assert.throws(() => parsePivotFormulaFieldValue(field, 1));
            assert.throws(() => parsePivotFormulaFieldValue(field, "won"));
        }
    });
});
