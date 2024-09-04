/** @ts-check */
import { describe, expect, test } from "@odoo/hoot";
import { getRelativeDateInterval } from "@spreadsheet/global_filters/relative_date_helpers";
import { serializeDate } from "@web/core/l10n/dates";

describe.current.tags("headless");

const { DateTime } = luxon;

/**
 * Assert that the given internal begins and ends at the expected dates.
 *
 * @param {luxon.Interval} interval
 * @param {string} start
 * @param {string} end
 */
function assertIntervalsEqual(interval, start, end) {
    expect(serializeDate(interval.start)).toBe(start);
    expect(serializeDate(interval.end)).toBe(end);
}

function checkRelativeDate(now, value, start, end, offset = 0) {
    const interval = getRelativeDateInterval(
        DateTime.fromISO(now, { locale: "en" }),
        value,
        offset
    );
    assertIntervalsEqual(interval, start, end);
}

test("getRelativeDateInterval > day", function () {
    checkRelativeDate("2022-05-16", { reference: "this", unit: "day" }, "2022-05-16", "2022-05-16");

    checkRelativeDate(
        "2022-05-16",
        { reference: "next", unit: "day", interval: 1 },
        "2022-05-17",
        "2022-05-17"
    );
    checkRelativeDate(
        "2022-05-16",
        { reference: "next", unit: "day", interval: 30 },
        "2022-05-17",
        "2022-06-15"
    );

    checkRelativeDate(
        "2022-05-16",
        { reference: "last", unit: "day", interval: 1 },
        "2022-05-15",
        "2022-05-15"
    );
    checkRelativeDate(
        "2022-05-16",
        { reference: "last", unit: "day", interval: 30 },
        "2022-04-16",
        "2022-05-15"
    );
});

test("getRelativeDateInterval > week", function () {
    checkRelativeDate(
        "2022-05-16",
        { reference: "this", unit: "week" },
        "2022-05-16",
        "2022-05-22"
    );

    checkRelativeDate(
        "2022-05-16",
        { reference: "next", unit: "week", interval: 1 },
        "2022-05-23",
        "2022-05-29"
    );
    checkRelativeDate(
        "2022-05-16",
        { reference: "next", unit: "week", interval: 4 },
        "2022-05-23",
        "2022-06-19"
    );

    checkRelativeDate(
        "2022-05-16",
        { reference: "last", unit: "week", interval: 1 },
        "2022-05-09",
        "2022-05-15"
    );
    checkRelativeDate(
        "2022-05-16",
        { reference: "last", unit: "week", interval: 4 },
        "2022-04-18",
        "2022-05-15"
    );
});

test("getRelativeDateInterval > month", function () {
    checkRelativeDate(
        "2022-05-16",
        { reference: "this", unit: "month" },
        "2022-05-01",
        "2022-05-31"
    );

    checkRelativeDate(
        "2022-05-16",
        { reference: "next", unit: "month", interval: 1 },
        "2022-06-01",
        "2022-06-30"
    );
    checkRelativeDate(
        "2022-05-16",
        { reference: "next", unit: "month", interval: 6 },
        "2022-06-01",
        "2022-11-30"
    );

    checkRelativeDate(
        "2022-05-16",
        { reference: "last", unit: "month", interval: 1 },
        "2022-04-01",
        "2022-04-30"
    );
    checkRelativeDate(
        "2022-05-16",
        { reference: "last", unit: "month", interval: 6 },
        "2021-11-01",
        "2022-04-30"
    );
});

test("getRelativeDateInterval > quarter", function () {
    checkRelativeDate(
        "2022-05-16",
        { reference: "this", unit: "quarter" },
        "2022-04-01",
        "2022-06-30"
    );

    checkRelativeDate(
        "2022-05-16",
        { reference: "next", unit: "quarter", interval: 1 },
        "2022-07-01",
        "2022-09-30"
    );
    checkRelativeDate(
        "2022-05-16",
        { reference: "next", unit: "quarter", interval: 4 },
        "2022-07-01",
        "2023-06-30"
    );

    checkRelativeDate(
        "2022-05-16",
        { reference: "last", unit: "quarter", interval: 1 },
        "2022-01-01",
        "2022-03-31"
    );
    checkRelativeDate(
        "2022-05-16",
        { reference: "last", unit: "quarter", interval: 4 },
        "2021-04-01",
        "2022-03-31"
    );
});

test("getRelativeDateInterval > year", function () {
    checkRelativeDate(
        "2022-05-16",
        { reference: "this", unit: "year" },
        "2022-01-01",
        "2022-12-31"
    );

    checkRelativeDate(
        "2022-05-16",
        { reference: "next", unit: "year", interval: 1 },
        "2023-01-01",
        "2023-12-31"
    );
    checkRelativeDate(
        "2022-05-16",
        { reference: "next", unit: "year", interval: 5 },
        "2023-01-01",
        "2027-12-31"
    );

    checkRelativeDate(
        "2022-05-16",
        { reference: "last", unit: "year", interval: 1 },
        "2021-01-01",
        "2021-12-31"
    );
    checkRelativeDate(
        "2022-05-16",
        { reference: "last", unit: "year", interval: 5 },
        "2017-01-01",
        "2021-12-31"
    );
});

test("getRelativeDateInterval > month_to_date", function () {
    checkRelativeDate(
        "2022-05-16",
        { reference: "this", unit: "month_to_date" },
        "2022-04-17",
        "2022-05-16"
    );

    checkRelativeDate(
        "2022-05-16",
        { reference: "next", unit: "month_to_date", interval: 1 },
        "2022-05-17",
        "2022-06-16"
    );
    checkRelativeDate(
        "2022-05-16",
        { reference: "next", unit: "month_to_date", interval: 3 },
        "2022-05-17",
        "2022-08-16"
    );

    checkRelativeDate(
        "2022-05-16",
        { reference: "last", unit: "month_to_date", interval: 1 },
        "2022-04-17",
        "2022-05-16"
    );
    checkRelativeDate(
        "2022-05-16",
        { reference: "last", unit: "month_to_date", interval: 3 },
        "2022-02-17",
        "2022-05-16"
    );
});

test("getRelativeDateInterval > week_to_date", function () {
    checkRelativeDate(
        "2022-05-16",
        { reference: "this", unit: "week_to_date" },
        "2022-05-10",
        "2022-05-16"
    );

    checkRelativeDate(
        "2022-05-16",
        { reference: "next", unit: "week_to_date", interval: 1 },
        "2022-05-17",
        "2022-05-23"
    );
    checkRelativeDate(
        "2022-05-16",
        { reference: "next", unit: "week_to_date", interval: 4 },
        "2022-05-17",
        "2022-06-13"
    );

    checkRelativeDate(
        "2022-05-16",
        { reference: "last", unit: "week_to_date", interval: 1 },
        "2022-05-10",
        "2022-05-16"
    );
    checkRelativeDate(
        "2022-05-16",
        { reference: "last", unit: "week_to_date", interval: 4 },
        "2022-04-19",
        "2022-05-16"
    );
});

test("getRelativeDateInterval > year_to_date", function () {
    checkRelativeDate(
        "2022-05-16",
        { reference: "this", unit: "year_to_date" },
        "2021-05-17",
        "2022-05-16"
    );

    checkRelativeDate(
        "2022-05-16",
        { reference: "next", unit: "year_to_date", interval: 1 },
        "2022-05-17",
        "2023-05-16"
    );
    checkRelativeDate(
        "2022-05-16",
        { reference: "next", unit: "year_to_date", interval: 3 },
        "2022-05-17",
        "2025-05-16"
    );

    checkRelativeDate(
        "2022-05-16",
        { reference: "last", unit: "year_to_date", interval: 1 },
        "2021-05-17",
        "2022-05-16"
    );
    checkRelativeDate(
        "2022-05-16",
        { reference: "last", unit: "year_to_date", interval: 3 },
        "2019-05-17",
        "2022-05-16"
    );
});

test("getRelativeDateInterval with offset > day", function () {
    checkRelativeDate(
        "2022-05-16",
        { reference: "this", unit: "day" },
        "2022-05-14",
        "2022-05-14",
        -2
    );

    checkRelativeDate(
        "2022-05-16",
        { reference: "this", unit: "day" },
        "2022-05-18",
        "2022-05-18",
        2
    );

    checkRelativeDate(
        "2022-05-16",
        { reference: "last", unit: "day", interval: 2 },
        "2022-05-10",
        "2022-05-11",
        -2
    );

    checkRelativeDate(
        "2022-05-16",
        { reference: "last", unit: "day", interval: 2 },
        "2022-05-18",
        "2022-05-19",
        2
    );

    checkRelativeDate(
        "2022-05-16",
        { reference: "next", unit: "day", interval: 2 },
        "2022-05-13",
        "2022-05-14",
        -2
    );

    checkRelativeDate(
        "2022-05-16",
        { reference: "next", unit: "day", interval: 2 },
        "2022-05-21",
        "2022-05-22",
        2
    );
});

test("getRelativeDateInterval with offset > week", function () {
    checkRelativeDate(
        "2022-05-16",
        { reference: "this", unit: "week" },
        "2022-05-02",
        "2022-05-08",
        -2
    );

    checkRelativeDate(
        "2022-05-16",
        { reference: "this", unit: "week" },
        "2022-05-30",
        "2022-06-05",
        2
    );

    checkRelativeDate(
        "2022-05-16",
        { reference: "last", unit: "week", interval: 2 },
        "2022-04-04",
        "2022-04-17",
        -2
    );

    checkRelativeDate(
        "2022-05-16",
        { reference: "last", unit: "week", interval: 2 },
        "2022-05-30",
        "2022-06-12",
        2
    );

    checkRelativeDate(
        "2022-05-16",
        { reference: "next", unit: "week", interval: 2 },
        "2022-04-25",
        "2022-05-08",
        -2
    );

    checkRelativeDate(
        "2022-05-16",
        { reference: "next", unit: "week", interval: 2 },
        "2022-06-20",
        "2022-07-03",
        2
    );
});

test("getRelativeDateInterval with offset > month", function () {
    checkRelativeDate(
        "2022-05-16",
        { reference: "this", unit: "month" },
        "2022-03-01",
        "2022-03-31",
        -2
    );

    checkRelativeDate(
        "2022-05-16",
        { reference: "this", unit: "month" },
        "2022-07-01",
        "2022-07-31",
        2
    );

    checkRelativeDate(
        "2022-05-16",
        { reference: "last", unit: "month", interval: 2 },
        "2021-11-01",
        "2021-12-31",
        -2
    );

    checkRelativeDate(
        "2022-05-16",
        { reference: "last", unit: "month", interval: 2 },
        "2022-07-01",
        "2022-08-31",
        2
    );

    checkRelativeDate(
        "2022-05-16",
        { reference: "next", unit: "month", interval: 2 },
        "2022-02-01",
        "2022-03-31",
        -2
    );

    checkRelativeDate(
        "2022-05-16",
        { reference: "next", unit: "month", interval: 2 },
        "2022-10-01",
        "2022-11-30",
        2
    );
});

test("getRelativeDateInterval with offset > quarter", function () {
    checkRelativeDate(
        "2022-05-16",
        { reference: "this", unit: "quarter" },
        "2021-10-01",
        "2021-12-31",
        -2
    );

    checkRelativeDate(
        "2022-05-16",
        { reference: "this", unit: "quarter" },
        "2022-10-01",
        "2022-12-31",
        2
    );

    checkRelativeDate(
        "2022-05-16",
        { reference: "last", unit: "quarter", interval: 2 },
        "2020-10-01",
        "2021-03-31",
        -2
    );

    checkRelativeDate(
        "2022-05-16",
        { reference: "last", unit: "quarter", interval: 2 },
        "2022-10-01",
        "2023-03-31",
        2
    );

    checkRelativeDate(
        "2022-05-16",
        { reference: "next", unit: "quarter", interval: 2 },
        "2021-07-01",
        "2021-12-31",
        -2
    );

    checkRelativeDate(
        "2022-05-16",
        { reference: "next", unit: "quarter", interval: 2 },
        "2023-07-01",
        "2023-12-31",
        2
    );
});

test("getRelativeDateInterval with offset > year", function () {
    checkRelativeDate(
        "2022-05-16",
        { reference: "this", unit: "year" },
        "2020-01-01",
        "2020-12-31",
        -2
    );

    checkRelativeDate(
        "2022-05-16",
        { reference: "this", unit: "year" },
        "2024-01-01",
        "2024-12-31",
        2
    );

    checkRelativeDate(
        "2022-05-16",
        { reference: "last", unit: "year", interval: 2 },
        "2016-01-01",
        "2017-12-31",
        -2
    );

    checkRelativeDate(
        "2022-05-16",
        { reference: "last", unit: "year", interval: 2 },
        "2024-01-01",
        "2025-12-31",
        2
    );

    checkRelativeDate(
        "2022-05-16",
        { reference: "next", unit: "year", interval: 2 },
        "2019-01-01",
        "2020-12-31",
        -2
    );

    checkRelativeDate(
        "2022-05-16",
        { reference: "next", unit: "year", interval: 2 },
        "2027-01-01",
        "2028-12-31",
        2
    );
});

test("getRelativeDateInterval with offset > month_to_date", function () {
    checkRelativeDate(
        "2022-05-16",
        { reference: "this", unit: "month_to_date" },
        "2022-02-17",
        "2022-03-16",
        -2
    );

    checkRelativeDate(
        "2022-05-16",
        { reference: "this", unit: "month_to_date" },
        "2022-06-17",
        "2022-07-16",
        2
    );

    checkRelativeDate(
        "2022-05-16",
        { reference: "last", unit: "month_to_date", interval: 2 },
        "2021-11-17",
        "2022-01-16",
        -2
    );

    checkRelativeDate(
        "2022-05-16",
        { reference: "last", unit: "month_to_date", interval: 2 },
        "2022-07-17",
        "2022-09-16",
        2
    );

    checkRelativeDate(
        "2022-05-16",
        { reference: "next", unit: "month_to_date", interval: 2 },
        "2022-01-17",
        "2022-03-16",
        -2
    );

    checkRelativeDate(
        "2022-05-16",
        { reference: "next", unit: "month_to_date", interval: 2 },
        "2022-09-17",
        "2022-11-16",
        2
    );
});

test("getRelativeDateInterval with offset > week_to_date", function () {
    checkRelativeDate(
        "2022-05-16",
        { reference: "this", unit: "week_to_date" },
        "2022-04-26",
        "2022-05-02",
        -2
    );

    checkRelativeDate(
        "2022-05-16",
        { reference: "this", unit: "week_to_date" },
        "2022-05-24",
        "2022-05-30",
        2
    );

    checkRelativeDate(
        "2022-05-16",
        { reference: "last", unit: "week_to_date", interval: 2 },
        "2022-04-05",
        "2022-04-18",
        -2
    );

    checkRelativeDate(
        "2022-05-16",
        { reference: "last", unit: "week_to_date", interval: 2 },
        "2022-05-31",
        "2022-06-13",
        2
    );

    checkRelativeDate(
        "2022-05-16",
        { reference: "next", unit: "week_to_date", interval: 2 },
        "2022-04-19",
        "2022-05-02",
        -2
    );

    checkRelativeDate(
        "2022-05-16",
        { reference: "next", unit: "week_to_date", interval: 2 },
        "2022-06-14",
        "2022-06-27",
        2
    );
});

test("getRelativeDateInterval with offset > year_to_date", function () {
    checkRelativeDate(
        "2022-05-16",
        { reference: "this", unit: "year_to_date" },
        "2019-05-17",
        "2020-05-16",
        -2
    );

    checkRelativeDate(
        "2022-05-16",
        { reference: "this", unit: "year_to_date" },
        "2023-05-17",
        "2024-05-16",
        2
    );

    checkRelativeDate(
        "2022-05-16",
        { reference: "last", unit: "year_to_date", interval: 2 },
        "2016-05-17",
        "2018-05-16",
        -2
    );

    checkRelativeDate(
        "2022-05-16",
        { reference: "last", unit: "year_to_date", interval: 2 },
        "2024-05-17",
        "2026-05-16",
        2
    );

    checkRelativeDate(
        "2022-05-16",
        { reference: "next", unit: "year_to_date", interval: 2 },
        "2018-05-17",
        "2020-05-16",
        -2
    );

    checkRelativeDate(
        "2022-05-16",
        { reference: "next", unit: "year_to_date", interval: 2 },
        "2026-05-17",
        "2028-05-16",
        2
    );
});
