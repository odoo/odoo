/** @odoo-module */
import { getFirstPivotFunction, getNumberOfPivotFormulas } from "@spreadsheet/pivot/pivot_helpers";
import { getFirstListFunction, getNumberOfListFormulas } from "@spreadsheet/list/list_helpers";
import { toNormalizedPivotValue } from "@spreadsheet/pivot/pivot_model";
import { pivotTimeAdapter } from "@spreadsheet/pivot/pivot_time_adapters";
import { constants, tokenize } from "@odoo/o-spreadsheet";
const { DEFAULT_LOCALE } = constants;

function stringArg(value) {
    return { type: "STRING", value: `${value}` };
}

QUnit.module("spreadsheet > pivot_helpers", {}, () => {
    QUnit.test("Basic formula extractor", async function (assert) {
        const formula = `=ODOO.PIVOT("1", "test") + ODOO.LIST("2", "hello", "bla")`;
        const tokens = tokenize(formula);
        let functionName;
        let args;
        ({ functionName, args } = getFirstPivotFunction(tokens));
        assert.strictEqual(functionName, "ODOO.PIVOT");
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
        const formula = `=ODOO.PIVOT("1", "test") + ODOO.PIVOT("2", "hello", "bla")`;
        const tokens = tokenize(formula);
        const { functionName, args } = getFirstPivotFunction(tokens);
        assert.strictEqual(functionName, "ODOO.PIVOT");
        assert.strictEqual(args.length, 2);
        assert.deepEqual(args[0], stringArg("1"));
        assert.deepEqual(args[1], stringArg("test"));
        assert.strictEqual(getFirstListFunction(tokens), undefined);
    });

    QUnit.test("Number of formulas", async function (assert) {
        const formula = `=ODOO.PIVOT("1", "test") + ODOO.PIVOT("2", "hello", "bla") + ODOO.LIST("1", "bla")`;
        assert.strictEqual(getNumberOfPivotFormulas(tokenize(formula)), 2);
        assert.strictEqual(getNumberOfListFormulas(tokenize(formula)), 1);
        assert.strictEqual(getNumberOfPivotFormulas(tokenize("=1+1")), 0);
        assert.strictEqual(getNumberOfListFormulas(tokenize("=1+1")), 0);
        assert.strictEqual(getNumberOfPivotFormulas(tokenize("=bla")), 0);
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
            const field = {
                type: fieldType,
                string: "A field",
            };
            assert.strictEqual(toNormalizedPivotValue(field, "won"), "won");
            assert.strictEqual(toNormalizedPivotValue(field, "1"), "1");
            assert.strictEqual(toNormalizedPivotValue(field, 1), "1");
            assert.strictEqual(toNormalizedPivotValue(field, "11/2020"), "11/2020");
            assert.strictEqual(toNormalizedPivotValue(field, "2020"), "2020");
            assert.strictEqual(toNormalizedPivotValue(field, "01/11/2020"), "01/11/2020");
            assert.strictEqual(toNormalizedPivotValue(field, "false"), false);
            assert.strictEqual(toNormalizedPivotValue(field, false), false);
            assert.strictEqual(toNormalizedPivotValue(field, "true"), "true");
        }
    });

    QUnit.test("parse values of time fields", (assert) => {
        for (const fieldType of ["date", "datetime"]) {
            const field = {
                type: fieldType,
                string: "A field",
            };
            // day
            assert.strictEqual(toNormalizedPivotValue(field, "1/11/2020", "day"), "01/11/2020");
            assert.strictEqual(toNormalizedPivotValue(field, "01/11/2020", "day"), "01/11/2020");
            assert.strictEqual(toNormalizedPivotValue(field, "11/2020", "day"), "11/01/2020");
            assert.strictEqual(toNormalizedPivotValue(field, "1", "day"), "12/31/1899");
            assert.strictEqual(toNormalizedPivotValue(field, 1, "day"), "12/31/1899");
            assert.strictEqual(toNormalizedPivotValue(field, "false", "day"), false);
            assert.strictEqual(toNormalizedPivotValue(field, false, "day"), false);
            // week
            assert.strictEqual(toNormalizedPivotValue(field, "11/2020", "week"), "11/2020");
            assert.strictEqual(toNormalizedPivotValue(field, "1/2020", "week"), "1/2020");
            assert.strictEqual(toNormalizedPivotValue(field, "01/2020", "week"), "1/2020");
            assert.strictEqual(toNormalizedPivotValue(field, "false", "week"), false);
            assert.strictEqual(toNormalizedPivotValue(field, false, "week"), false);
            // month
            assert.strictEqual(toNormalizedPivotValue(field, "11/2020", "month"), "11/2020");
            assert.strictEqual(toNormalizedPivotValue(field, "1/2020", "month"), "01/2020");
            assert.strictEqual(toNormalizedPivotValue(field, "01/2020", "month"), "01/2020");
            assert.strictEqual(toNormalizedPivotValue(field, "2/11/2020", "month"), "02/2020");
            assert.strictEqual(toNormalizedPivotValue(field, "2/1/2020", "month"), "02/2020");
            assert.strictEqual(toNormalizedPivotValue(field, 1, "month"), "12/1899");
            assert.strictEqual(toNormalizedPivotValue(field, "false", "month"), false);
            assert.strictEqual(toNormalizedPivotValue(field, false, "month"), false);
            // year
            assert.strictEqual(toNormalizedPivotValue(field, "2020", "year"), 2020);
            assert.strictEqual(toNormalizedPivotValue(field, 2020, "year"), 2020);
            assert.strictEqual(toNormalizedPivotValue(field, "false", "year"), false);
            assert.strictEqual(toNormalizedPivotValue(field, false, "year"), false);

            assert.throws(() => toNormalizedPivotValue(field, "true", "month"));
            assert.throws(() => toNormalizedPivotValue(field, true, "month"));
            assert.throws(() => toNormalizedPivotValue(field, "won", "month"));
        }
    });

    QUnit.test("parse values of boolean field", (assert) => {
        const field = {
            type: "boolean",
            string: "A field",
        };
        assert.strictEqual(toNormalizedPivotValue(field, "false"), false);
        assert.strictEqual(toNormalizedPivotValue(field, false), false);
        assert.strictEqual(toNormalizedPivotValue(field, "true"), true);
        assert.strictEqual(toNormalizedPivotValue(field, true), true);
        assert.throws(() => toNormalizedPivotValue(field, "11/2020"));
        assert.throws(() => toNormalizedPivotValue(field, "2020"));
        assert.throws(() => toNormalizedPivotValue(field, "01/11/2020"));
        assert.throws(() => toNormalizedPivotValue(field, "1"));
        assert.throws(() => toNormalizedPivotValue(field, 1));
        assert.throws(() => toNormalizedPivotValue(field, "won"));
    });

    QUnit.test("parse values of numeric fields", (assert) => {
        for (const fieldType of ["float", "integer", "monetary", "many2one", "many2many"]) {
            const field = {
                type: fieldType,
                string: "A field",
            };
            assert.strictEqual(toNormalizedPivotValue(field, "2020"), 2020);
            assert.strictEqual(toNormalizedPivotValue(field, "01/11/2020"), 43841); // a date is actually a number in a spreadsheet
            assert.strictEqual(toNormalizedPivotValue(field, "11/2020"), 44136); // 1st of november 2020
            assert.strictEqual(toNormalizedPivotValue(field, "1"), 1);
            assert.strictEqual(toNormalizedPivotValue(field, 1), 1);
            assert.strictEqual(toNormalizedPivotValue(field, "false"), false);
            assert.strictEqual(toNormalizedPivotValue(field, false), false);
            assert.throws(() => toNormalizedPivotValue(field, "true"));
            assert.throws(() => toNormalizedPivotValue(field, true));
            assert.throws(() => toNormalizedPivotValue(field, "won"));
        }
    });

    QUnit.test("parse values of unsupported fields", (assert) => {
        for (const fieldType of ["one2many", "binary", "html"]) {
            const field = {
                type: fieldType,
                string: "A field",
            };
            assert.throws(() => toNormalizedPivotValue(field, "false"));
            assert.throws(() => toNormalizedPivotValue(field, false));
            assert.throws(() => toNormalizedPivotValue(field, "true"));
            assert.throws(() => toNormalizedPivotValue(field, true));
            assert.throws(() => toNormalizedPivotValue(field, "11/2020"));
            assert.throws(() => toNormalizedPivotValue(field, "2020"));
            assert.throws(() => toNormalizedPivotValue(field, "01/11/2020"));
            assert.throws(() => toNormalizedPivotValue(field, "1"));
            assert.throws(() => toNormalizedPivotValue(field, 1));
            assert.throws(() => toNormalizedPivotValue(field, "won"));
        }
    });
});

QUnit.module("spreadsheet > pivot time adapters formatted value", {}, () => {
    QUnit.test("Day adapter", (assert) => {
        const adapter = pivotTimeAdapter("day");
        assert.strictEqual(adapter.format("11/12/2020", DEFAULT_LOCALE), "11/12/2020");
        assert.strictEqual(adapter.format("01/11/2020", DEFAULT_LOCALE), "1/11/2020");
        assert.strictEqual(adapter.format("12/05/2020", DEFAULT_LOCALE), "12/5/2020");
    });

    QUnit.test("Week adapter", (assert) => {
        const adapter = pivotTimeAdapter("week");
        assert.strictEqual(adapter.format("5/2024", DEFAULT_LOCALE), "W5 2024");
        assert.strictEqual(adapter.format("51/2020", DEFAULT_LOCALE), "W51 2020");
    });

    QUnit.test("Month adapter", (assert) => {
        const adapter = pivotTimeAdapter("month");
        assert.strictEqual(adapter.format("12/2020", DEFAULT_LOCALE), "December 2020");
        assert.strictEqual(adapter.format("02/2020", DEFAULT_LOCALE), "February 2020");
    });

    QUnit.test("Quarter adapter", (assert) => {
        const adapter = pivotTimeAdapter("quarter");
        assert.strictEqual(adapter.format("1/2022", DEFAULT_LOCALE), "Q1 2022");
        assert.strictEqual(adapter.format("3/1998", DEFAULT_LOCALE), "Q3 1998");
    });

    QUnit.test("Year adapter", (assert) => {
        const adapter = pivotTimeAdapter("year");
        assert.strictEqual(adapter.format("2020", DEFAULT_LOCALE), "2020");
        assert.strictEqual(adapter.format("1997", DEFAULT_LOCALE), "1997");
    });
});
