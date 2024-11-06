/** @ts-check */
import { describe, expect, test } from "@odoo/hoot";
import { getRelativeDateDomain } from "@spreadsheet/global_filters/relative_date_helpers";
import {
    getDateDomainDurationInDays,
    assertDateDomainEqual,
} from "@spreadsheet/../tests/helpers/date_domain";

describe.current.tags("headless");

const { DateTime } = luxon;

test("getRelativeDateDomain > year_to_date (year to date)", async function () {
    const now = DateTime.fromISO("2022-05-16");
    const domain = getRelativeDateDomain(
        now,
        0,
        { reference: "this", unit: "year_to_date" },
        "field",
        "date"
    );
    assertDateDomainEqual("field", "2021-05-17", "2022-05-16", domain);
});

test("getRelativeDateDomain > quarter", async function () {
    const now = DateTime.fromISO("2022-05-16");
    const domain = getRelativeDateDomain(
        now,
        0,
        { reference: "this", unit: "quarter" },
        "field",
        "date"
    );
    assertDateDomainEqual("field", "2022-04-01", "2022-06-30", domain);
});

test("getRelativeDateDomain > last_week (last 7 days)", async function () {
    const now = DateTime.fromISO("2022-05-16");
    const domain = getRelativeDateDomain(
        now,
        0,
        { reference: "last", unit: "day", interval: 7 },
        "field",
        "date"
    );
    expect(getDateDomainDurationInDays(domain)).toBe(7);
    assertDateDomainEqual("field", "2022-05-09", "2022-05-15", domain);
});

test("getRelativeDateDomain > last_month (last 30 days)", async function () {
    const now = DateTime.fromISO("2022-05-16");
    const domain = getRelativeDateDomain(
        now,
        0,
        { reference: "last", unit: "day", interval: 30 },
        "field",
        "date"
    );
    expect(getDateDomainDurationInDays(domain)).toBe(30);
    assertDateDomainEqual("field", "2022-04-16", "2022-05-15", domain);
});

test("getRelativeDateDomain > last_three_months (last 90 days)", async function () {
    const now = DateTime.fromISO("2022-05-16");
    const domain = getRelativeDateDomain(
        now,
        0,
        { reference: "last", unit: "day", interval: 90 },
        "field",
        "date"
    );
    expect(getDateDomainDurationInDays(domain)).toBe(90);
    assertDateDomainEqual("field", "2022-02-15", "2022-05-15", domain);
});

test("getRelativeDateDomain > last_six_months (last 180 days)", async function () {
    const now = DateTime.fromISO("2022-05-16");
    const domain = getRelativeDateDomain(
        now,
        0,
        { reference: "last", unit: "day", interval: 180 },
        "field",
        "date"
    );
    expect(getDateDomainDurationInDays(domain)).toBe(180);
    assertDateDomainEqual("field", "2021-11-17", "2022-05-15", domain);
});

test("getRelativeDateDomain > last_year (last 365 days)", async function () {
    const now = DateTime.fromISO("2022-05-16");
    const domain = getRelativeDateDomain(
        now,
        0,
        { reference: "last", unit: "day", interval: 365 },
        "field",
        "date"
    );
    expect(getDateDomainDurationInDays(domain)).toBe(365);
    assertDateDomainEqual("field", "2021-05-16", "2022-05-15", domain);
});

test("getRelativeDateDomain > last_three_years (last 3 * 365 days)", async function () {
    const now = DateTime.fromISO("2022-05-16");
    const domain = getRelativeDateDomain(
        now,
        0,
        { reference: "last", unit: "day", interval: 3 * 365 },
        "field",
        "date"
    );
    expect(getDateDomainDurationInDays(domain)).toBe(3 * 365);
    assertDateDomainEqual("field", "2019-05-17", "2022-05-15", domain);
});

test("getRelativeDateDomain > simple date time", async function () {
    const now = DateTime.fromISO("2022-05-16T00:00:00+00:00", { zone: "utc" });
    const domain = getRelativeDateDomain(
        now,
        0,
        { reference: "last", unit: "day", interval: 7 },
        "field",
        "datetime"
    );
    expect(getDateDomainDurationInDays(domain)).toBe(7);
    assertDateDomainEqual("field", "2022-05-09 00:00:00", "2022-05-15 23:59:59", domain);
});

test("getRelativeDateDomain > date time from middle of day", async function () {
    const now = DateTime.fromISO("2022-05-16T13:59:00+00:00", { zone: "utc" });
    const domain = getRelativeDateDomain(
        now,
        0,
        { reference: "last", unit: "day", interval: 7 },
        "field",
        "datetime"
    );
    expect(getDateDomainDurationInDays(domain)).toBe(7);
    assertDateDomainEqual("field", "2022-05-09 00:00:00", "2022-05-15 23:59:59", domain);
});

test("getRelativeDateDomain > date time with timezone", async function () {
    const now = DateTime.fromISO("2022-05-16T12:00:00+02:00", { zone: "UTC+2" });
    const domain = getRelativeDateDomain(
        now,
        0,
        { reference: "last", unit: "day", interval: 7 },
        "field",
        "datetime"
    );
    expect(getDateDomainDurationInDays(domain)).toBe(7);
    assertDateDomainEqual("field", "2022-05-08 22:00:00", "2022-05-15 21:59:59", domain);
});

test("getRelativeDateDomain > date time with timezone on different day than UTC", async function () {
    const now = DateTime.fromISO("2022-05-16T01:00:00+02:00", { zone: "UTC+2" });
    const domain = getRelativeDateDomain(
        now,
        0,
        { reference: "last", unit: "day", interval: 7 },
        "field",
        "datetime"
    );
    expect(getDateDomainDurationInDays(domain)).toBe(7);
    assertDateDomainEqual("field", "2022-05-08 22:00:00", "2022-05-15 21:59:59", domain);
});

test("getRelativeDateDomain > with offset > year_to_date (year to date)", async function () {
    const now = DateTime.fromISO("2022-05-16");
    const domain = getRelativeDateDomain(
        now,
        -1,
        {
            reference: "this",
            unit: "year_to_date",
        },
        "field",
        "date"
    );
    assertDateDomainEqual("field", "2020-05-17", "2021-05-16", domain);
});

test("getRelativeDateDomain > with offset > last_week (last 7 days)", async function () {
    const now = DateTime.fromISO("2022-05-16");
    const domain = getRelativeDateDomain(
        now,
        -1,
        { reference: "last", unit: "day", interval: 7 },
        "field",
        "date"
    );
    expect(getDateDomainDurationInDays(domain)).toBe(7);
    assertDateDomainEqual("field", "2022-05-02", "2022-05-08", domain);
});

test("getRelativeDateDomain > with offset (last 30 days)", async function () {
    const now = DateTime.fromISO("2022-05-16");
    const domain = getRelativeDateDomain(
        now,
        -2,
        { reference: "last", unit: "day", interval: 30 },
        "field",
        "date"
    );
    expect(getDateDomainDurationInDays(domain)).toBe(30);
    assertDateDomainEqual("field", "2022-02-15", "2022-03-16", domain);
});

test("getRelativeDateDomain > with offset > last_year (last 365 days)", async function () {
    const now = DateTime.fromISO("2022-05-16");
    const domain = getRelativeDateDomain(
        now,
        1,
        { reference: "last", unit: "day", interval: 365 },
        "field",
        "date"
    );
    expect(getDateDomainDurationInDays(domain)).toBe(365);
    assertDateDomainEqual("field", "2022-05-16", "2023-05-15", domain);
});

test("getRelativeDateDomain > with offset > last_three_years (last 3 * 365 days)", async function () {
    const now = DateTime.fromISO("2022-05-16");
    const domain = getRelativeDateDomain(
        now,
        -1,
        { reference: "last", unit: "day", interval: 3 * 365 },
        "field",
        "date"
    );
    expect(getDateDomainDurationInDays(domain)).toBe(3 * 365);
    assertDateDomainEqual("field", "2016-05-17", "2019-05-16", domain);
});

test("getRelativeDateDomain > with offset > simple date time", async function () {
    const now = DateTime.fromISO("2022-05-16T00:00:00+00:00", { zone: "utc" });
    const domain = getRelativeDateDomain(
        now,
        -1,
        { reference: "last", unit: "day", interval: 7 },
        "field",
        "datetime"
    );
    expect(getDateDomainDurationInDays(domain)).toBe(7);
    assertDateDomainEqual("field", "2022-05-02 00:00:00", "2022-05-08 23:59:59", domain);
});
