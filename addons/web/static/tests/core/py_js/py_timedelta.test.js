import { describe, expect, test } from "@odoo/hoot";

import { evaluateExpr } from "@web/core/py_js/py";
import { PyTimeDelta } from "@web/core/py_js/py_date";

const expectDelta = (expr, res) => {
    const timedelta = evaluateExpr(expr, { td: PyTimeDelta });
    expect(`${timedelta.days}, ${timedelta.seconds}, ${timedelta.microseconds}`).toBe(res);
};

const expectEquality = (expr1, expr2, ctx) => {
    const equality = `${expr1} == ${expr2}`;
    expect(evaluateExpr(equality, Object.assign({ td: PyTimeDelta }, ctx))).toBe(true, {
        message: `evaluating ${equality}`,
    });
};

describe.current.tags("headless");

test("create", () => {
    expectDelta("td(weeks=1)", "7, 0, 0");
    expectDelta("td(days=1)", "1, 0, 0");
    expectDelta("td(hours=1)", "0, 3600, 0");
    expectDelta("td(minutes=1)", "0, 60, 0");
    expectDelta("td(seconds=1)", "0, 1, 0");
    expectDelta("td(milliseconds=1)", "0, 0, 1000");
    expectDelta("td(microseconds=1)", "0, 0, 1");

    expectDelta("td(days=-1.25)", "-2, 64800, 0");
    expectDelta("td(seconds=129600.4)", "1, 43200, 400000");
    expectDelta("td(hours=24.5,milliseconds=1400)", "1, 1801, 400000");

    expectEquality(
        "td()",
        "td(weeks=0, days=0, hours=0, minutes=0, seconds=0, milliseconds=0, microseconds=0)"
    );
    expectEquality("td(1)", "td(days=1)");
    expectEquality("td(0, 1)", "td(seconds=1)");
    expectEquality("td(0, 0, 1)", "td(microseconds=1)");
    expectEquality("td(weeks=1)", "td(days=7)");
    expectEquality("td(days=1)", "td(hours=24)");
    expectEquality("td(hours=1)", "td(minutes=60)");
    expectEquality("td(minutes=1)", "td(seconds=60)");
    expectEquality("td(seconds=1)", "td(milliseconds=1000)");
    expectEquality("td(milliseconds=1)", "td(microseconds=1000)");

    expectEquality("td(weeks=1.0/7)", "td(days=1)");
    expectEquality("td(days=1.0/24)", "td(hours=1)");
    expectEquality("td(hours=1.0/60)", "td(minutes=1)");
    expectEquality("td(minutes=1.0/60)", "td(seconds=1)");
    expectEquality("td(seconds=0.001)", "td(milliseconds=1)");
    expectEquality("td(milliseconds=0.001)", "td(microseconds=1)");
});

test("massive normalization", () => {
    expect.assertions(3);

    const td = PyTimeDelta.create({ microseconds: -1 });

    expect(td.days).toBe(-1);
    expect(td.seconds).toBe(24 * 3600 - 1);
    expect(td.microseconds).toBe(999999);
});

test("attributes", () => {
    expect.assertions(3);

    const ctx = { td: PyTimeDelta };

    expect(evaluateExpr("td(1, 7, 31).days", ctx)).toBe(1);
    expect(evaluateExpr("td(1, 7, 31).seconds", ctx)).toBe(7);
    expect(evaluateExpr("td(1, 7, 31).microseconds", ctx)).toBe(31);
});

test("basic operations: +, -, *, //", () => {
    expect.assertions(28);

    const ctx = {
        a: new PyTimeDelta(7, 0, 0),
        b: new PyTimeDelta(0, 60, 0),
        c: new PyTimeDelta(0, 0, 1000),
    };

    expectEquality("a+b+c", "td(7, 60, 1000)", ctx);
    expectEquality("a-b", "td(6, 24*3600 - 60)", ctx);
    expectEquality("-a", "td(-7)", ctx);
    expectEquality("+a", "td(7)", ctx);
    expectEquality("-b", "td(-1, 24*3600 - 60)", ctx);
    expectEquality("-c", "td(-1, 24*3600 - 1, 999000)", ctx);
    expectEquality("td(6, 24*3600)", "a", ctx);
    expectEquality("td(0, 0, 60*1000000)", "b", ctx);
    expectEquality("a*10", "td(70)", ctx);
    expectEquality("a*10", "10*a", ctx);
    // expectEquality('a*10L', '10*a', ctx);
    expectEquality("b*10", "td(0, 600)", ctx);
    expectEquality("10*b", "td(0, 600)", ctx);
    // expectEquality('b*10L', 'td(0, 600)', ctx);
    expectEquality("c*10", "td(0, 0, 10000)", ctx);
    expectEquality("10*c", "td(0, 0, 10000)", ctx);
    // expectEquality('c*10L', 'td(0, 0, 10000)', ctx);
    expectEquality("a*-1", "-a", ctx);
    expectEquality("b*-2", "-b-b", ctx);
    expectEquality("c*-2", "-c+-c", ctx);
    expectEquality("b*(60*24)", "(b*60)*24", ctx);
    expectEquality("b*(60*24)", "(60*b)*24", ctx);
    expectEquality("c*1000", "td(0, 1)", ctx);
    expectEquality("1000*c", "td(0, 1)", ctx);
    expectEquality("a//7", "td(1)", ctx);
    expectEquality("b//10", "td(0, 6)", ctx);
    expectEquality("c//1000", "td(0, 0, 1)", ctx);
    expectEquality("a//10", "td(0, 7*24*360)", ctx);
    expectEquality("a//3600000", "td(0, 0, 7*24*1000)", ctx);
    expectEquality("td(999999999, 86399, 999999) - td(999999999, 86399, 999998)", "td(0, 0, 1)");
    expectEquality("td(999999999, 1, 1) - td(999999999, 1, 0)", "td(0, 0, 1)");
});

test("total_seconds", () => {
    expect.assertions(6);

    const ctx = { td: PyTimeDelta };

    expect(evaluateExpr("td(365).total_seconds()", ctx)).toBe(31536000);
    expect(evaluateExpr("td(seconds=123456.789012).total_seconds()", ctx)).toBe(123456.789012);
    expect(evaluateExpr("td(seconds=-123456.789012).total_seconds()", ctx)).toBe(-123456.789012);
    expect(evaluateExpr("td(seconds=0.123456).total_seconds()", ctx)).toBe(0.123456);
    expect(evaluateExpr("td().total_seconds()", ctx)).toBe(0);
    expect(evaluateExpr("td(seconds=1000000).total_seconds()", ctx)).toBe(1e6);
});

test("bool", () => {
    expect.assertions(5);

    const ctx = { td: PyTimeDelta };

    expect(evaluateExpr("bool(td(1))", ctx)).toBe(true);
    expect(evaluateExpr("bool(td(0, 1))", ctx)).toBe(true);
    expect(evaluateExpr("bool(td(0, 0, 1))", ctx)).toBe(true);
    expect(evaluateExpr("bool(td(microseconds=1))", ctx)).toBe(true);
    expect(evaluateExpr("bool(not td(0))", ctx)).toBe(true);
});
