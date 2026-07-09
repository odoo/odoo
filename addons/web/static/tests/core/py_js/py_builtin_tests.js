/** @odoo-module **/

import { evaluateExpr } from "@web/core/py_js/py";
import { BUILTINS } from "@web/core/py_js/py_builtin";
import { patchDate, patchTimeZone } from "@web/../tests/helpers/utils";

QUnit.module("py", {}, () => {
    QUnit.module("builtins", () => {
        QUnit.module("context_today");

        QUnit.test("context_today()", (assert) => {
            patchTimeZone(0)
            patchDate(2023, 11, 31, 23, 30, 0);

            const expected = luxon.DateTime.now().toUTC().toFormat("yyyy-MM-dd");

            assert.strictEqual(BUILTINS.context_today().strftime("%Y-%m-%d"), expected);
            assert.strictEqual(evaluateExpr("context_today().strftime('%Y-%m-%d')"), expected);
        });

        QUnit.test("context_today() + 2h", (assert) => {
            patchTimeZone(0)
            patchDate(2023, 11, 31, 23, 30, 0);

            const expected = luxon.DateTime.now().toUTC().toFormat("yyyy-MM-dd");

            patchTimeZone(120)
            patchDate(2024, 0, 1, 1, 30, 0);

            assert.strictEqual(BUILTINS.context_today().strftime("%Y-%m-%d"), expected);
            assert.strictEqual(evaluateExpr("context_today().strftime('%Y-%m-%d')"), expected);
        });

        QUnit.test("context_today() + 1d", (assert) => {
            patchTimeZone(0)
            patchDate(2023, 11, 31, 23, 30, 0);

            const expected = luxon.DateTime.now().toUTC().plus({ days: 1 }).toFormat("yyyy-MM-dd");

            assert.strictEqual(evaluateExpr("(context_today() + datetime.timedelta(days=1)).strftime('%Y-%m-%d')"), expected);
        });

        QUnit.module("today");

        QUnit.test("today", (assert) => {
            patchTimeZone(0)
            patchDate(2023, 11, 31, 23, 30, 0);

            const expected = luxon.DateTime.now().toUTC().toFormat("yyyy-MM-dd");

            assert.strictEqual(BUILTINS.today, expected);
            assert.strictEqual(evaluateExpr("today"), expected);
        });

        QUnit.test("today + 2h", (assert) => {
            patchTimeZone(0)
            patchDate(2023, 11, 31, 23, 30, 0);

            const expected = luxon.DateTime.now().toUTC().toFormat("yyyy-MM-dd");

            patchTimeZone(120)
            patchDate(2024, 0, 1, 1, 30, 0);

            assert.strictEqual(BUILTINS.today, expected);
            assert.strictEqual(evaluateExpr("today"), expected);
        });

        QUnit.module("now");

        QUnit.test("now", (assert) => {
            patchTimeZone(0)
            patchDate(2023, 11, 31, 23, 30, 0);

            const expected = luxon.DateTime.now().toUTC().toFormat("yyyy-MM-dd HH:mm:ss");

            assert.strictEqual(BUILTINS.now, expected);
            assert.strictEqual(evaluateExpr("now"), expected);
        });

        QUnit.test("now + 2h", (assert) => {
            patchTimeZone(0)
            patchDate(2023, 11, 31, 23, 30, 0);

            const expected = luxon.DateTime.now().toUTC().toFormat("yyyy-MM-dd HH:mm:ss");

            patchTimeZone(120)
            patchDate(2024, 0, 1, 1, 30, 0);

            assert.strictEqual(BUILTINS.now, expected);
            assert.strictEqual(evaluateExpr("now"), expected);
        });

        QUnit.module("time");

        QUnit.test("time", (assert) => {
            patchTimeZone(0)
            patchDate(2023, 11, 31, 23, 30, 0);

            const expected = luxon.DateTime.now().toUTC().toFormat("yyyy-MM-dd HH:mm:ss");

            assert.strictEqual(BUILTINS.time.strftime('%Y-%m-%d %H:%M:%S'), expected);
            assert.strictEqual(evaluateExpr("time.strftime('%Y-%m-%d %H:%M:%S')"), expected);
        });

        QUnit.test("time + 2h", (assert) => {
            patchTimeZone(0)
            patchDate(2023, 11, 31, 23, 30, 0);

            const expected = luxon.DateTime.now().toUTC().toFormat("yyyy-MM-dd HH:mm:ss");

            patchTimeZone(120)
            patchDate(2024, 0, 1, 1, 30, 0);

            assert.strictEqual(BUILTINS.time.strftime('%Y-%m-%d %H:%M:%S'), expected);
            assert.strictEqual(evaluateExpr("time.strftime('%Y-%m-%d %H:%M:%S')"), expected);
        });

        QUnit.module("current_date");

        QUnit.test("current_date", (assert) => {
            patchTimeZone(0)
            patchDate(2023, 11, 31, 23, 30, 0);

            const expected = luxon.DateTime.now().toUTC().toFormat("yyyy-MM-dd");

            assert.strictEqual(BUILTINS.current_date, expected);
            assert.strictEqual(evaluateExpr("current_date"), expected);
        });

        QUnit.test("current_date + 2h", (assert) => {
            patchTimeZone(0)
            patchDate(2023, 11, 31, 23, 30, 0);

            const expected = luxon.DateTime.now().toUTC().toFormat("yyyy-MM-dd");

            patchTimeZone(120)
            patchDate(2024, 0, 1, 1, 30, 0);

            assert.strictEqual(BUILTINS.current_date, expected);
            assert.strictEqual(evaluateExpr("current_date"), expected);
        });

        QUnit.module("XML eval");

        QUnit.test("builtins in domain do not shift date", (assert) => {
            patchTimeZone(0)
            patchDate(2023, 11, 31, 23, 30, 0);

            const expected = luxon.DateTime.now().toUTC()
            const expectedDate = expected.toFormat("yyyy-MM-dd");
            const expectedDateTime = expected.toFormat("yyyy-MM-dd HH:mm:ss");

            const resultContext = evaluateExpr("[('date_field', '<=', context_today())]");
            assert.ok(Array.isArray(resultContext));
            assert.strictEqual(resultContext[0][2].day, expected.day);
            assert.strictEqual(resultContext[0][2].month, expected.month);
            assert.strictEqual(resultContext[0][2].year, expected.year);

            const resultTime = evaluateExpr("[('date_field', '<=', time.strftime('%Y-%m-%d %H:%M:%S'))]");
            assert.ok(Array.isArray(resultTime));
            assert.strictEqual(resultTime[0][2], expectedDateTime);

            const resultCurrent = evaluateExpr("[('date_field', '<=', current_date)]");
            assert.ok(Array.isArray(resultCurrent));
            assert.strictEqual(resultCurrent[0][2], expectedDate);
        });
    });
});
