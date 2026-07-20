import { describe, expect, test } from "@odoo/hoot";
import { mockDate, mockTimeZone } from "@odoo/hoot-mock";
import { evaluateExpr } from "@web/core/py_js/py";
import { BUILTINS } from "@web/core/py_js/py_builtin";

describe.current.tags("headless");

describe("context_today", () => {
    test("context_today()", () => {
        mockTimeZone("Etc/UTC");
        mockDate("2023-12-31 23:30:00");

        const expected = luxon.DateTime.now().toUTC().toFormat("yyyy-MM-dd");

        expect(BUILTINS.context_today().strftime("%Y-%m-%d")).toBe(expected);
        expect(evaluateExpr("context_today().strftime('%Y-%m-%d')")).toBe(expected);
    });

    test("context_today() + 2h", () => {
        mockTimeZone("Etc/UTC");
        mockDate("2023-12-31 23:30:00");

        const expected = luxon.DateTime.now().toUTC().toFormat("yyyy-MM-dd");

        mockTimeZone(+2);

        expect(BUILTINS.context_today().strftime("%Y-%m-%d")).toBe(expected);
        expect(evaluateExpr("context_today().strftime('%Y-%m-%d')")).toBe(expected);
    });

    test("context_today() + 1d", () => {
        mockTimeZone("Etc/UTC");
        mockDate("2023-12-31 23:30:00");

        const expected = luxon.DateTime.now().toUTC().plus({ days: 1 }).toFormat("yyyy-MM-dd");

        expect(evaluateExpr("(context_today() + datetime.timedelta(days=1)).strftime('%Y-%m-%d')")).toBe(expected);
    });
});

describe("today", () => {
    test("today", () => {
        mockTimeZone("Etc/UTC");
        mockDate("2023-12-31 23:30:00");

        const expected = luxon.DateTime.now().toUTC().toFormat("yyyy-MM-dd");

        expect(BUILTINS.today).toBe(expected);
        expect(evaluateExpr("today")).toBe(expected);
    });

    test("today + 2h", () => {
        mockTimeZone("Etc/UTC");
        mockDate("2023-12-31 23:30:00");

        const expected = luxon.DateTime.now().toUTC().toFormat("yyyy-MM-dd");

        mockTimeZone(+2);

        expect(BUILTINS.today).toBe(expected);
        expect(evaluateExpr("today")).toBe(expected);
    });
});

describe("now", () => {
    test("now", () => {
        mockTimeZone("Etc/UTC");
        mockDate("2023-12-31 23:30:00");

        const expected = luxon.DateTime.now().toUTC().toFormat("yyyy-MM-dd HH:mm:ss");

        expect(BUILTINS.now).toBe(expected);
        expect(evaluateExpr("now")).toBe(expected);
    });

    test("now + 2h", () => {
        mockTimeZone("Etc/UTC");
        mockDate("2023-12-31 23:30:00");

        const expected = luxon.DateTime.now().toUTC().toFormat("yyyy-MM-dd HH:mm:ss");

        mockTimeZone(+2);

        expect(BUILTINS.now).toBe(expected);
        expect(evaluateExpr("now")).toBe(expected);
    });
});

describe("time", () => {
    test("time", () => {
        mockTimeZone("Etc/UTC");
        mockDate("2023-12-31 23:30:00");

        const expected = luxon.DateTime.now().toUTC().toFormat("yyyy-MM-dd HH:mm:ss");

        expect(BUILTINS.time.strftime("%Y-%m-%d %H:%M:%S")).toBe(expected);
        expect(evaluateExpr("time.strftime('%Y-%m-%d %H:%M:%S')")).toBe(expected);
    });

    test("time + 2h", () => {
        mockTimeZone("Etc/UTC");
        mockDate("2023-12-31 23:30:00");

        const expected = luxon.DateTime.now().toUTC().toFormat("yyyy-MM-dd HH:mm:ss");

        mockTimeZone(+2);

        expect(BUILTINS.time.strftime("%Y-%m-%d %H:%M:%S")).toBe(expected);
        expect(evaluateExpr("time.strftime('%Y-%m-%d %H:%M:%S')")).toBe(expected);
    });
});

describe("current_date", () => {
    test("current_date", () => {
        mockTimeZone("Etc/UTC");
        mockDate("2023-12-31 23:30:00");

        const expected = luxon.DateTime.now().toUTC().toFormat("yyyy-MM-dd");

        expect(BUILTINS.current_date).toBe(expected);
        expect(evaluateExpr("current_date")).toBe(expected);
    });

    test("current_date + 2h", () => {
        mockTimeZone("Etc/UTC");
        mockDate("2023-12-31 23:30:00");

        const expected = luxon.DateTime.now().toUTC().toFormat("yyyy-MM-dd");

        mockTimeZone(+2);

        expect(BUILTINS.current_date).toBe(expected);
        expect(evaluateExpr("current_date")).toBe(expected);
    });
});

describe("XML eval", () => {
    test("builtins in domain do not shift date", () => {
        mockTimeZone("Etc/UTC");
        mockDate("2023-12-31 23:30:00");

        const expected = luxon.DateTime.now().toUTC();
        const expectedDate = expected.toFormat("yyyy-MM-dd");
        const expectedDateTime = expected.toFormat("yyyy-MM-dd HH:mm:ss");

        const resultContext = evaluateExpr("[('date_field', '<=', context_today())]");
        expect(Array.isArray(resultContext)).toBe(true);
        expect(resultContext[0][2].day).toBe(expected.day);
        expect(resultContext[0][2].month).toBe(expected.month);
        expect(resultContext[0][2].year).toBe(expected.year);

        const resultTime = evaluateExpr("[('date_field', '<=', time.strftime('%Y-%m-%d %H:%M:%S'))]");
        expect(Array.isArray(resultTime)).toBe(true);
        expect(resultTime[0][2]).toBe(expectedDateTime);

        const resultCurrent = evaluateExpr("[('date_field', '<=', current_date)]");
        expect(Array.isArray(resultCurrent)).toBe(true);
        expect(resultCurrent[0][2]).toBe(expectedDate);
    });
});
