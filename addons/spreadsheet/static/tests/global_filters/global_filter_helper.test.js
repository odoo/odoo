/** @ts-check */
import { describe, expect, test, beforeEach } from "@odoo/hoot";
import {
    getDateDomain,
    getRelativeDateFromTo,
    dateFilterValueToString,
} from "@spreadsheet/global_filters/helpers";
import {
    getDateDomainDurationInDays,
    assertDateDomainEqual,
} from "@spreadsheet/../tests/helpers/date_domain";
import { patchTranslations } from "@web/../tests/web_test_helpers";

describe.current.tags("headless");

const { DateTime } = luxon;

beforeEach(() => {
    patchTranslations();
});

function getRelativeDateDomain(now, offset, period, fieldName, fieldType) {
    const { from, to } = getRelativeDateFromTo(now, offset, period);
    return getDateDomain(from, to, fieldName, fieldType);
}

function valueToString(value) {
    return dateFilterValueToString(value).toString();
}

test("getRelativeDateDomain > year_to_date (year to date)", async function () {
    const now = DateTime.fromISO("2022-05-16");
    const domain = getRelativeDateDomain(now, 0, "year_to_date", "field", "date");
    assertDateDomainEqual("field", "2022-01-01", "2022-05-16", domain);
});

test("getRelativeDateDomain > today (today)", async function () {
    const now = DateTime.fromISO("2022-05-16");
    const domain = getRelativeDateDomain(now, 0, "today", "field", "date");
    expect(getDateDomainDurationInDays(domain)).toBe(1);
    assertDateDomainEqual("field", "2022-05-16", "2022-05-16", domain);
});

test("getRelativeDateDomain > yesterday (yesterday)", async function () {
    const now = DateTime.fromISO("2022-05-16");
    const domain = getRelativeDateDomain(now, 0, "yesterday", "field", "date");
    expect(getDateDomainDurationInDays(domain)).toBe(1);
    assertDateDomainEqual("field", "2022-05-15", "2022-05-15", domain);
});

test("getRelativeDateDomain > last_7_days (last 7 days)", async function () {
    const now = DateTime.fromISO("2022-05-16");
    const domain = getRelativeDateDomain(now, 0, "last_7_days", "field", "date");
    expect(getDateDomainDurationInDays(domain)).toBe(7);
    assertDateDomainEqual("field", "2022-05-10", "2022-05-16", domain);
});

test("getRelativeDateDomain > last_30_days (last 30 days)", async function () {
    const now = DateTime.fromISO("2022-05-16");
    const domain = getRelativeDateDomain(now, 0, "last_30_days", "field", "date");
    expect(getDateDomainDurationInDays(domain)).toBe(30);
    assertDateDomainEqual("field", "2022-04-17", "2022-05-16", domain);
});

test("getRelativeDateDomain > last_90_days (last 90 days)", async function () {
    const now = DateTime.fromISO("2022-05-16");
    const domain = getRelativeDateDomain(now, 0, "last_90_days", "field", "date");
    expect(getDateDomainDurationInDays(domain)).toBe(90);
    assertDateDomainEqual("field", "2022-02-16", "2022-05-16", domain);
});

test("getRelativeDateDomain > month_to_date (Month to Date)", async function () {
    const now = DateTime.fromISO("2022-05-16");
    const domain = getRelativeDateDomain(now, 0, "month_to_date", "field", "date");
    expect(getDateDomainDurationInDays(domain)).toBe(16);
    assertDateDomainEqual("field", "2022-05-01", "2022-05-16", domain);
});

test("getRelativeDateDomain > last_month (Last month)", async function () {
    const now = DateTime.fromISO("2022-05-16");
    const domain = getRelativeDateDomain(now, 0, "last_month", "field", "date");
    expect(getDateDomainDurationInDays(domain)).toBe(30);
    assertDateDomainEqual("field", "2022-04-01", "2022-04-30", domain);
});

test("getRelativeDateDomain > last_12_months (last 12 months)", async function () {
    const now = DateTime.fromISO("2022-05-16");
    const domain = getRelativeDateDomain(now, 0, "last_12_months", "field", "date");
    expect(getDateDomainDurationInDays(domain)).toBe(365);
    assertDateDomainEqual("field", "2021-05-01", "2022-04-30", domain);
});

test("getRelativeDateDomain > simple date time", async function () {
    const now = DateTime.fromISO("2022-05-16T00:00:00+00:00", { zone: "utc" });
    const domain = getRelativeDateDomain(now, 0, "last_7_days", "field", "datetime");
    expect(getDateDomainDurationInDays(domain)).toBe(7);
    assertDateDomainEqual("field", "2022-05-10 00:00:00", "2022-05-16 23:59:59", domain);
});

test("getRelativeDateDomain > date time from middle of day", async function () {
    const now = DateTime.fromISO("2022-05-16T13:59:00+00:00", { zone: "utc" });
    const domain = getRelativeDateDomain(now, 0, "last_7_days", "field", "datetime");
    expect(getDateDomainDurationInDays(domain)).toBe(7);
    assertDateDomainEqual("field", "2022-05-10 00:00:00", "2022-05-16 23:59:59", domain);
});

test("getRelativeDateDomain > date time with timezone", async function () {
    const now = DateTime.fromISO("2022-05-16T12:00:00+02:00", { zone: "UTC+2" });
    const domain = getRelativeDateDomain(now, 0, "last_7_days", "field", "datetime");
    expect(getDateDomainDurationInDays(domain)).toBe(7);
    assertDateDomainEqual("field", "2022-05-09 22:00:00", "2022-05-16 21:59:59", domain);
});

test("getRelativeDateDomain > date time with timezone on different day than UTC", async function () {
    const now = DateTime.fromISO("2022-05-16T01:00:00+02:00", { zone: "UTC+2" });
    const domain = getRelativeDateDomain(now, 0, "last_7_days", "field", "datetime");
    expect(getDateDomainDurationInDays(domain)).toBe(7);
    assertDateDomainEqual("field", "2022-05-09 22:00:00", "2022-05-16 21:59:59", domain);
});

test("getRelativeDateDomain > with offset > year_to_date (year to date)", async function () {
    const now = DateTime.fromISO("2022-05-16");
    const domain = getRelativeDateDomain(now, -1, "year_to_date", "field", "date");
    assertDateDomainEqual("field", "2021-01-01", "2021-05-16", domain);
});

test("getRelativeDateDomain > with offset > today (today)", async function () {
    const now = DateTime.fromISO("2022-05-16");
    const domain = getRelativeDateDomain(now, -1, "today", "field", "date");
    expect(getDateDomainDurationInDays(domain)).toBe(1);
    assertDateDomainEqual("field", "2022-05-15", "2022-05-15", domain);
});

test("getRelativeDateDomain > with offset > yesterday (yesterday)", async function () {
    const now = DateTime.fromISO("2022-05-16");
    const domain = getRelativeDateDomain(now, -1, "yesterday", "field", "date");
    expect(getDateDomainDurationInDays(domain)).toBe(1);
    assertDateDomainEqual("field", "2022-05-14", "2022-05-14", domain);
});

test("getRelativeDateDomain > with offset > last_7_days (last 7 days)", async function () {
    const now = DateTime.fromISO("2022-05-16");
    const domain = getRelativeDateDomain(now, -1, "last_7_days", "field", "date");
    expect(getDateDomainDurationInDays(domain)).toBe(7);
    assertDateDomainEqual("field", "2022-05-03", "2022-05-09", domain);
});

test("getRelativeDateDomain > with offset (last 30 days)", async function () {
    const now = DateTime.fromISO("2022-05-16");
    const domain = getRelativeDateDomain(now, -2, "last_30_days", "field", "date");
    expect(getDateDomainDurationInDays(domain)).toBe(30);
    assertDateDomainEqual("field", "2022-02-16", "2022-03-17", domain);
});

test("getRelativeDateDomain > with offset > month_to_date (Month to Date)", async function () {
    const now = DateTime.fromISO("2022-05-16");
    const domain = getRelativeDateDomain(now, -1, "month_to_date", "field", "date");
    expect(getDateDomainDurationInDays(domain)).toBe(16);
    assertDateDomainEqual("field", "2022-04-01", "2022-04-16", domain);
});

test("getRelativeDateDomain > with offset > last_month (Last month)", async function () {
    const now = DateTime.fromISO("2022-05-16");
    const domain = getRelativeDateDomain(now, -1, "last_month", "field", "date");
    expect(getDateDomainDurationInDays(domain)).toBe(31);
    assertDateDomainEqual("field", "2022-03-01", "2022-03-31", domain);
});

test("getRelativeDateDomain > with offset > last_12_months (last 12 months)", async function () {
    const now = DateTime.fromISO("2022-05-16");
    const domain = getRelativeDateDomain(now, 1, "last_12_months", "field", "date");
    expect(getDateDomainDurationInDays(domain)).toBe(365);
    assertDateDomainEqual("field", "2022-05-01", "2023-04-30", domain);
});

test("getRelativeDateDomain > with offset > simple date time", async function () {
    const now = DateTime.fromISO("2022-05-16T00:00:00+00:00", { zone: "utc" });
    const domain = getRelativeDateDomain(now, -1, "last_7_days", "field", "datetime");
    expect(getDateDomainDurationInDays(domain)).toBe(7);
    assertDateDomainEqual("field", "2022-05-03 00:00:00", "2022-05-09 23:59:59", domain);
});

test("dateFilterValueToString > relative periods", function () {
    expect(valueToString({ type: "relative", period: "today" })).toBe("Today");
    expect(valueToString({ type: "relative", period: "yesterday" })).toBe("Yesterday");
    expect(valueToString({ type: "relative", period: "last_7_days" })).toBe("Last 7 Days");
    expect(valueToString({ type: "relative", period: "last_30_days" })).toBe("Last 30 Days");
    expect(valueToString({ type: "relative", period: "last_90_days" })).toBe("Last 90 Days");
    expect(valueToString({ type: "relative", period: "month_to_date" })).toBe("Month to Date");
    expect(valueToString({ type: "relative", period: "last_month" })).toBe("Last Month");
    expect(valueToString({ type: "relative", period: "year_to_date" })).toBe("Year to Date");
    expect(valueToString({ type: "relative", period: "last_12_months" })).toBe("Last 12 Months");
});
test("dateFilterValueToString > month", function () {
    expect(valueToString({ type: "month", year: 2022, month: 5 })).toBe("May 2022");
});

test("dateFilterValueToString > quarter", function () {
    expect(valueToString({ type: "quarter", year: 2022, quarter: 2 })).toBe("Q2 2022");
});

test("dateFilterValueToString > year", function () {
    expect(valueToString({ type: "year", year: 2022 })).toBe("2022");
});

test("dateFilterValueToString > range", function () {
    expect(valueToString({ type: "range", from: "2022-01-01", to: "2022-12-31" })).toBe(
        "2022-01-01 to 2022-12-31"
    );
    expect(valueToString({ type: "range", from: "2022-01-01" })).toBe("2022-01-01 to all time");
    expect(valueToString({ type: "range", to: "2022-12-31" })).toBe("All time to 2022-12-31");
    expect(valueToString({ type: "range" })).toBe("All time");
});

test("dateFilterValueToString > all time", function () {
    expect(valueToString({ type: undefined })).toBe("All time");
    expect(valueToString({})).toBe("All time");
});

test("dateFilterValueToString > invalid value", function () {
    expect(valueToString({ type: "invalid" })).toBe("All time");
    expect(valueToString(undefined)).toBe("All time");
});
