/** @odoo-module */
import { getFirstListFunction, getNumberOfListFormulas } from "@spreadsheet/list/list_helpers";
import { constants, tokenize, helpers } from "@odoo/o-spreadsheet";
const {
    getFirstPivotFunction,
    getNumberOfPivotFunctions,
    pivotTimeAdapter,
    toNormalizedPivotValue,
} = helpers;
const { DEFAULT_LOCALE } = constants;

function stringArg(value) {
    return { type: "STRING", value: `${value}` };
}

QUnit.module("spreadsheet > pivot_helpers", {}, () => {
    QUnit.test("Basic formula extractor", async function (assert) {
        const formula = `=PIVOT.VALUE("1", "test") + ODOO.LIST("2", "hello", "bla")`;
        const tokens = tokenize(formula);
        let functionName;
        let args;
        ({ functionName, args } = getFirstPivotFunction(tokens));
        assert.strictEqual(functionName, "PIVOT.VALUE");
        assert.strictEqual(args.length, 2);
        assert.deepEqual(args[0], stringArg("1"));
        assert.deepEqual(args[1], stringArg("test"));
        ({ functionName, args } = getFirstListFunction(tokens));
        assert.strictEqual(functionName, "ODOO.LIST");
        assert.strictEqual(args.length, 3);
        assert.deepEqual(args[0], stringArg("2"));
        assert.deepEqual(args[1], stringArg("hello"));
        assert.deepEqual(args[2], stringArg("bla"));
    });

    QUnit.test("Extraction with two PIVOT formulas", async function (assert) {
        const formula = `=PIVOT.VALUE("1", "test") + PIVOT.VALUE("2", "hello", "bla")`;
        const tokens = tokenize(formula);
        const { functionName, args } = getFirstPivotFunction(tokens);
        assert.strictEqual(functionName, "PIVOT.VALUE");
        assert.strictEqual(args.length, 2);
        assert.deepEqual(args[0], stringArg("1"));
        assert.deepEqual(args[1], stringArg("test"));
        assert.strictEqual(getFirstListFunction(tokens), undefined);
    });

    QUnit.test("Number of formulas", async function (assert) {
        const formula = `=PIVOT.VALUE("1", "test") + PIVOT.VALUE("2", "hello", "bla") + ODOO.LIST("1", "bla")`;
        assert.strictEqual(getNumberOfPivotFunctions(tokenize(formula)), 2);
        assert.strictEqual(getNumberOfListFormulas(tokenize(formula)), 1);
        assert.strictEqual(getNumberOfPivotFunctions(tokenize("=1+1")), 0);
        assert.strictEqual(getNumberOfListFormulas(tokenize("=1+1")), 0);
        assert.strictEqual(getNumberOfPivotFunctions(tokenize("=bla")), 0);
        assert.strictEqual(getNumberOfListFormulas(tokenize("=bla")), 0);
    });

    QUnit.test("getFirstPivotFunction does not crash when given crap", async function (assert) {
        assert.strictEqual(getFirstListFunction(tokenize("=SUM(A1)")), undefined);
        assert.strictEqual(getFirstPivotFunction(tokenize("=SUM(A1)")), undefined);
        assert.strictEqual(getFirstListFunction(tokenize("=1+1")), undefined);
        assert.strictEqual(getFirstPivotFunction(tokenize("=1+1")), undefined);
        assert.strictEqual(getFirstListFunction(tokenize("=bla")), undefined);
        assert.strictEqual(getFirstPivotFunction(tokenize("=bla")), undefined);
        assert.strictEqual(getFirstListFunction(tokenize("bla")), undefined);
        assert.strictEqual(getFirstPivotFunction(tokenize("bla")), undefined);
    });
});

QUnit.module("spreadsheet > toNormalizedPivotValue", {}, () => {
    QUnit.test("parse values of a selection, char or text field", (assert) => {
        for (const fieldType of ["selection", "text", "char"]) {
            const dimension = {
                type: fieldType,
                displayName: "A field",
                name: "my_field_name",
            };
            assert.strictEqual(toNormalizedPivotValue(dimension, "won"), "won");
            assert.strictEqual(toNormalizedPivotValue(dimension, "1"), "1");
            assert.strictEqual(toNormalizedPivotValue(dimension, 1), "1");
            assert.strictEqual(toNormalizedPivotValue(dimension, "11/2020"), "11/2020");
            assert.strictEqual(toNormalizedPivotValue(dimension, "2020"), "2020");
            assert.strictEqual(toNormalizedPivotValue(dimension, "01/11/2020"), "01/11/2020");
            assert.strictEqual(toNormalizedPivotValue(dimension, "false"), false);
            assert.strictEqual(toNormalizedPivotValue(dimension, false), false);
            assert.strictEqual(toNormalizedPivotValue(dimension, "true"), "true");
        }
    });

    QUnit.test("parse values of time fields", (assert) => {
        for (const fieldType of ["date", "datetime"]) {
            const dimension = {
                type: fieldType,
                displayName: "A field",
                name: "my_field_name",
            };

            dimension.granularity = "day";
            assert.strictEqual(toNormalizedPivotValue(dimension, "1/11/2020"), "01/11/2020");
            assert.strictEqual(toNormalizedPivotValue(dimension, "01/11/2020"), "01/11/2020");
            assert.strictEqual(toNormalizedPivotValue(dimension, "11/2020"), "11/01/2020");
            assert.strictEqual(toNormalizedPivotValue(dimension, "1"), "12/31/1899");
            assert.strictEqual(toNormalizedPivotValue(dimension, 1), "12/31/1899");
            assert.strictEqual(toNormalizedPivotValue(dimension, "false"), false);
            assert.strictEqual(toNormalizedPivotValue(dimension, false), false);

            dimension.granularity = "week";
            assert.strictEqual(toNormalizedPivotValue(dimension, "11/2020"), "11/2020");
            assert.strictEqual(toNormalizedPivotValue(dimension, "1/2020"), "1/2020");
            assert.strictEqual(toNormalizedPivotValue(dimension, "01/2020"), "1/2020");
            assert.strictEqual(toNormalizedPivotValue(dimension, "false"), false);
            assert.strictEqual(toNormalizedPivotValue(dimension, false), false);

            dimension.granularity = "month";
            assert.strictEqual(toNormalizedPivotValue(dimension, "11/2020"), "11/2020");
            assert.strictEqual(toNormalizedPivotValue(dimension, "1/2020"), "01/2020");
            assert.strictEqual(toNormalizedPivotValue(dimension, "01/2020"), "01/2020");
            assert.strictEqual(toNormalizedPivotValue(dimension, "2/11/2020"), "02/2020");
            assert.strictEqual(toNormalizedPivotValue(dimension, "2/1/2020"), "02/2020");
            assert.strictEqual(toNormalizedPivotValue(dimension, 1), "12/1899");
            assert.strictEqual(toNormalizedPivotValue(dimension, "false"), false);
            assert.strictEqual(toNormalizedPivotValue(dimension, false), false);
            assert.throws(() => toNormalizedPivotValue(dimension, "true"));
            assert.throws(() => toNormalizedPivotValue(dimension, true));
            assert.throws(() => toNormalizedPivotValue(dimension, "won"));

            dimension.granularity = "year";
            assert.strictEqual(toNormalizedPivotValue(dimension, "2020"), 2020);
            assert.strictEqual(toNormalizedPivotValue(dimension, 2020), 2020);
            assert.strictEqual(toNormalizedPivotValue(dimension, "false"), false);
            assert.strictEqual(toNormalizedPivotValue(dimension, false), false);
        }
    });

    QUnit.test("parse values of boolean field", (assert) => {
        const dimension = {
            type: "boolean",
            displayName: "A field",
            name: "my_field_name",
        };
        assert.strictEqual(toNormalizedPivotValue(dimension, "false"), false);
        assert.strictEqual(toNormalizedPivotValue(dimension, false), false);
        assert.strictEqual(toNormalizedPivotValue(dimension, "true"), true);
        assert.strictEqual(toNormalizedPivotValue(dimension, true), true);
        assert.throws(() => toNormalizedPivotValue(dimension, "11/2020"));
        assert.throws(() => toNormalizedPivotValue(dimension, "2020"));
        assert.throws(() => toNormalizedPivotValue(dimension, "01/11/2020"));
        assert.throws(() => toNormalizedPivotValue(dimension, "1"));
        assert.throws(() => toNormalizedPivotValue(dimension, 1));
        assert.throws(() => toNormalizedPivotValue(dimension, "won"));
    });

    QUnit.test("parse values of numeric fields", (assert) => {
        for (const fieldType of ["float", "integer", "monetary", "many2one", "many2many"]) {
            const dimension = {
                type: fieldType,
                displayName: "A field",
                name: "my_field_name",
            };
            assert.strictEqual(toNormalizedPivotValue(dimension, "2020"), 2020);
            assert.strictEqual(toNormalizedPivotValue(dimension, "01/11/2020"), 43841); // a date is actually a number in a spreadsheet
            assert.strictEqual(toNormalizedPivotValue(dimension, "11/2020"), 44136); // 1st of november 2020
            assert.strictEqual(toNormalizedPivotValue(dimension, "1"), 1);
            assert.strictEqual(toNormalizedPivotValue(dimension, 1), 1);
            assert.strictEqual(toNormalizedPivotValue(dimension, "false"), false);
            assert.strictEqual(toNormalizedPivotValue(dimension, false), false);
            assert.throws(() => toNormalizedPivotValue(dimension, "true"));
            assert.throws(() => toNormalizedPivotValue(dimension, true));
            assert.throws(() => toNormalizedPivotValue(dimension, "won"));
        }
    });

    QUnit.test("parse values of unsupported fields", (assert) => {
        for (const fieldType of ["one2many", "binary", "html"]) {
            const dimension = {
                type: fieldType,
                displayName: "A field",
                name: "my_field_name",
            };
            assert.throws(() => toNormalizedPivotValue(dimension, "false"));
            assert.throws(() => toNormalizedPivotValue(dimension, false));
            assert.throws(() => toNormalizedPivotValue(dimension, "true"));
            assert.throws(() => toNormalizedPivotValue(dimension, true));
            assert.throws(() => toNormalizedPivotValue(dimension, "11/2020"));
            assert.throws(() => toNormalizedPivotValue(dimension, "2020"));
            assert.throws(() => toNormalizedPivotValue(dimension, "01/11/2020"));
            assert.throws(() => toNormalizedPivotValue(dimension, "1"));
            assert.throws(() => toNormalizedPivotValue(dimension, 1));
            assert.throws(() => toNormalizedPivotValue(dimension, "won"));
        }
    });
});

QUnit.module("spreadsheet > pivot time adapters formatted value", {}, () => {
    QUnit.test("Day adapter", (assert) => {
        const adapter = pivotTimeAdapter("day");
        assert.strictEqual(adapter.formatValue("11/12/2020", DEFAULT_LOCALE), "11/12/2020");
        assert.strictEqual(adapter.formatValue("01/11/2020", DEFAULT_LOCALE), "1/11/2020");
        assert.strictEqual(adapter.formatValue("12/05/2020", DEFAULT_LOCALE), "12/5/2020");
    });

    QUnit.test("Week adapter", (assert) => {
        const adapter = pivotTimeAdapter("week");
        assert.strictEqual(adapter.formatValue("5/2024", DEFAULT_LOCALE), "W5 2024");
        assert.strictEqual(adapter.formatValue("51/2020", DEFAULT_LOCALE), "W51 2020");
    });

    QUnit.test("Month adapter", (assert) => {
        const adapter = pivotTimeAdapter("month");
        assert.strictEqual(adapter.formatValue("12/2020", DEFAULT_LOCALE), "December 2020");
        assert.strictEqual(adapter.formatValue("02/2020", DEFAULT_LOCALE), "February 2020");
    });

    QUnit.test("Quarter adapter", (assert) => {
        const adapter = pivotTimeAdapter("quarter");
        assert.strictEqual(adapter.formatValue("1/2022", DEFAULT_LOCALE), "Q1 2022");
        assert.strictEqual(adapter.formatValue("3/1998", DEFAULT_LOCALE), "Q3 1998");
    });

    QUnit.test("Year adapter", (assert) => {
        const adapter = pivotTimeAdapter("year");
        assert.strictEqual(adapter.formatValue("2020", DEFAULT_LOCALE), "2020");
        assert.strictEqual(adapter.formatValue("1997", DEFAULT_LOCALE), "1997");
    });
});
