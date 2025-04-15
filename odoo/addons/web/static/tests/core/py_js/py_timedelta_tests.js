/** @odoo-module **/

import { evaluateExpr } from "@web/core/py_js/py";
import { PyTimeDelta } from "@web/core/py_js/py_date";

function testDelta(assert, expr, res) {
    const timedelta = evaluateExpr(expr, { td: PyTimeDelta });
    assert.strictEqual(`${timedelta.days}, ${timedelta.seconds}, ${timedelta.microseconds}`, res);
}

function testEquality(assert, expr1, expr2, ctx) {
    const equality = `${expr1} == ${expr2}`;
    assert.ok(
        evaluateExpr(equality, Object.assign({ td: PyTimeDelta }, ctx)),
        `evaluating ${equality}`
    );
}

QUnit.module("py", {}, () => {
    QUnit.module("datetime.timedelta");

    QUnit.test("create", (assert) => {
        testDelta(assert, "td(weeks=1)", "7, 0, 0");
        testDelta(assert, "td(days=1)", "1, 0, 0");
        testDelta(assert, "td(hours=1)", "0, 3600, 0");
        testDelta(assert, "td(minutes=1)", "0, 60, 0");
        testDelta(assert, "td(seconds=1)", "0, 1, 0");
        testDelta(assert, "td(milliseconds=1)", "0, 0, 1000");
        testDelta(assert, "td(microseconds=1)", "0, 0, 1");

        testDelta(assert, "td(days=-1.25)", "-2, 64800, 0");
        testDelta(assert, "td(seconds=129600.4)", "1, 43200, 400000");
        testDelta(assert, "td(hours=24.5,milliseconds=1400)", "1, 1801, 400000");

        testEquality(
            assert,
            "td()",
            "td(weeks=0, days=0, hours=0, minutes=0, seconds=0, milliseconds=0, microseconds=0)"
        );
        testEquality(assert, "td(1)", "td(days=1)");
        testEquality(assert, "td(0, 1)", "td(seconds=1)");
        testEquality(assert, "td(0, 0, 1)", "td(microseconds=1)");
        testEquality(assert, "td(weeks=1)", "td(days=7)");
        testEquality(assert, "td(days=1)", "td(hours=24)");
        testEquality(assert, "td(hours=1)", "td(minutes=60)");
        testEquality(assert, "td(minutes=1)", "td(seconds=60)");
        testEquality(assert, "td(seconds=1)", "td(milliseconds=1000)");
        testEquality(assert, "td(milliseconds=1)", "td(microseconds=1000)");

        testEquality(assert, "td(weeks=1.0/7)", "td(days=1)");
        testEquality(assert, "td(days=1.0/24)", "td(hours=1)");
        testEquality(assert, "td(hours=1.0/60)", "td(minutes=1)");
        testEquality(assert, "td(minutes=1.0/60)", "td(seconds=1)");
        testEquality(assert, "td(seconds=0.001)", "td(milliseconds=1)");
        testEquality(assert, "td(milliseconds=0.001)", "td(microseconds=1)");
    });

    QUnit.test("massive normalization", function (assert) {
        assert.expect(3);

        const td = PyTimeDelta.create({ microseconds: -1 });

        assert.strictEqual(td.days, -1);
        assert.strictEqual(td.seconds, 24 * 3600 - 1);
        assert.strictEqual(td.microseconds, 999999);
    });

    QUnit.test("attributes", function (assert) {
        assert.expect(3);

        const ctx = { td: PyTimeDelta };

        assert.strictEqual(evaluateExpr("td(1, 7, 31).days", ctx), 1);
        assert.strictEqual(evaluateExpr("td(1, 7, 31).seconds", ctx), 7);
        assert.strictEqual(evaluateExpr("td(1, 7, 31).microseconds", ctx), 31);
    });

    QUnit.test("basic operations: +, -, *, //", function (assert) {
        assert.expect(28);

        const ctx = {
            a: new PyTimeDelta(7, 0, 0),
            b: new PyTimeDelta(0, 60, 0),
            c: new PyTimeDelta(0, 0, 1000),
        };

        testEquality(assert, "a+b+c", "td(7, 60, 1000)", ctx);
        testEquality(assert, "a-b", "td(6, 24*3600 - 60)", ctx);
        testEquality(assert, "-a", "td(-7)", ctx);
        testEquality(assert, "+a", "td(7)", ctx);
        testEquality(assert, "-b", "td(-1, 24*3600 - 60)", ctx);
        testEquality(assert, "-c", "td(-1, 24*3600 - 1, 999000)", ctx);
        testEquality(assert, "td(6, 24*3600)", "a", ctx);
        testEquality(assert, "td(0, 0, 60*1000000)", "b", ctx);
        testEquality(assert, "a*10", "td(70)", ctx);
        testEquality(assert, "a*10", "10*a", ctx);
        // testEquality(assert, 'a*10L', '10*a', ctx);
        testEquality(assert, "b*10", "td(0, 600)", ctx);
        testEquality(assert, "10*b", "td(0, 600)", ctx);
        // testEquality(assert, 'b*10L', 'td(0, 600)', ctx);
        testEquality(assert, "c*10", "td(0, 0, 10000)", ctx);
        testEquality(assert, "10*c", "td(0, 0, 10000)", ctx);
        // testEquality(assert, 'c*10L', 'td(0, 0, 10000)', ctx);
        testEquality(assert, "a*-1", "-a", ctx);
        testEquality(assert, "b*-2", "-b-b", ctx);
        testEquality(assert, "c*-2", "-c+-c", ctx);
        testEquality(assert, "b*(60*24)", "(b*60)*24", ctx);
        testEquality(assert, "b*(60*24)", "(60*b)*24", ctx);
        testEquality(assert, "c*1000", "td(0, 1)", ctx);
        testEquality(assert, "1000*c", "td(0, 1)", ctx);
        testEquality(assert, "a//7", "td(1)", ctx);
        testEquality(assert, "b//10", "td(0, 6)", ctx);
        testEquality(assert, "c//1000", "td(0, 0, 1)", ctx);
        testEquality(assert, "a//10", "td(0, 7*24*360)", ctx);
        testEquality(assert, "a//3600000", "td(0, 0, 7*24*1000)", ctx);
        testEquality(
            assert,
            "td(999999999, 86399, 999999) - td(999999999, 86399, 999998)",
            "td(0, 0, 1)"
        );
        testEquality(assert, "td(999999999, 1, 1) - td(999999999, 1, 0)", "td(0, 0, 1)");
    });

    QUnit.test("total_seconds", function (assert) {
        assert.expect(6);

        const ctx = { td: PyTimeDelta };

        assert.strictEqual(evaluateExpr("td(365).total_seconds()", ctx), 31536000);
        assert.strictEqual(
            evaluateExpr("td(seconds=123456.789012).total_seconds()", ctx),
            123456.789012
        );
        assert.strictEqual(
            evaluateExpr("td(seconds=-123456.789012).total_seconds()", ctx),
            -123456.789012
        );
        assert.strictEqual(evaluateExpr("td(seconds=0.123456).total_seconds()", ctx), 0.123456);
        assert.strictEqual(evaluateExpr("td().total_seconds()", ctx), 0);
        assert.strictEqual(evaluateExpr("td(seconds=1000000).total_seconds()", ctx), 1e6);
    });

    QUnit.test("bool", function (assert) {
        assert.expect(5);

        const ctx = { td: PyTimeDelta };

        assert.ok(evaluateExpr("bool(td(1))", ctx));
        assert.ok(evaluateExpr("bool(td(0, 1))", ctx));
        assert.ok(evaluateExpr("bool(td(0, 0, 1))", ctx));
        assert.ok(evaluateExpr("bool(td(microseconds=1))", ctx));
        assert.ok(evaluateExpr("bool(not td(0))", ctx));
    });
});
