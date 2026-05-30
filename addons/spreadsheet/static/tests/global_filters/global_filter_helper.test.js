/** @ts-check */
import { describe, expect, test, beforeEach } from "@odoo/hoot";
import { mockDate } from "@odoo/hoot-mock";
import {
    getDateDomain,
    getRelativeDateFromTo,
    dateFilterValueToString,
    getNextDateFilterValue,
    getPreviousDateFilterValue,
    getFacetInfo,
    RELATIVE_PERIODS,
} from "@spreadsheet/global_filters/helpers";
import {
    getDateDomainDurationInDays,
    assertDateDomainEqual,
} from "@spreadsheet/../tests/helpers/date_domain";
import { makeMockEnv, allowTranslations } from "@web/../tests/web_test_helpers";
import { getOperatorLabel } from "@web/core/tree_editor/tree_editor_operator_editor";

import { defineSpreadsheetModels } from "../helpers/data";

describe.current.tags("headless");

const { DateTime } = luxon;

const LAZY_TRANSLATED_SET = getOperatorLabel("set");
const LAZY_TRANSLATED_NOT_SET = getOperatorLabel("not set");
const LAZY_TRANSLATED_CONTAINS = getOperatorLabel("ilike");

beforeEach(() => {
    allowTranslations();
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
        "January 1 – December 31, 2022"
    );
    expect(valueToString({ type: "range", from: "2022-01-01", to: "2022-01-01" })).toBe(
        "January 1, 2022"
    );
    expect(valueToString({ type: "range", from: "2022-01-01" })).toBe("Since January 1, 2022");
    expect(valueToString({ type: "range", to: "2022-12-31" })).toBe("Until December 31, 2022");
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

describe("getNextDateFilterValue", () => {
    test("month: December rolls over to January next year", () => {
        expect(getNextDateFilterValue({ type: "month", year: 2022, month: 12 })).toEqual({
            type: "month",
            year: 2023,
            month: 1,
        });
    });
    test("month: increments month", () => {
        expect(getNextDateFilterValue({ type: "month", year: 2022, month: 5 })).toEqual({
            type: "month",
            year: 2022,
            month: 6,
        });
    });
    test("quarter: Q4 rolls over to Q1 next year", () => {
        expect(getNextDateFilterValue({ type: "quarter", year: 2022, quarter: 4 })).toEqual({
            type: "quarter",
            year: 2023,
            quarter: 1,
        });
    });
    test("quarter: increments quarter", () => {
        expect(getNextDateFilterValue({ type: "quarter", year: 2022, quarter: 2 })).toEqual({
            type: "quarter",
            year: 2022,
            quarter: 3,
        });
    });
    test("year: increments year", () => {
        expect(getNextDateFilterValue({ type: "year", year: 2022 })).toEqual({
            type: "year",
            year: 2023,
        });
    });

    test("relative", () => {
        mockDate("2022-07-14 00:00:00");

        let result = getNextDateFilterValue({ type: "relative", period: "last_7_days" });
        expect(result).toEqual({
            type: "range",
            from: "2022-07-15",
            to: "2022-07-21",
        });

        result = getNextDateFilterValue({ type: "relative", period: "last_30_days" });
        expect(result).toEqual({
            type: "range",
            from: "2022-07-15",
            to: "2022-08-13",
        });

        result = getNextDateFilterValue({ type: "relative", period: "last_90_days" });
        expect(result).toEqual({
            type: "range",
            from: "2022-07-15",
            to: "2022-10-12",
        });

        result = getNextDateFilterValue({ type: "relative", period: "year_to_date" });
        expect(result).toEqual({
            type: "year",
            year: 2023,
        });

        result = getNextDateFilterValue({ type: "relative", period: "last_12_months" });
        expect(result).toEqual({
            type: "range",
            from: "2022-07-01",
            to: "2023-06-30",
        });

        result = getNextDateFilterValue({ type: "relative", period: "today" });
        expect(result).toEqual({
            type: "range",
            from: "2022-07-15",
            to: "2022-07-15",
        });

        result = getNextDateFilterValue({ type: "relative", period: "yesterday" });
        expect(result).toEqual({
            type: "range",
            from: "2022-07-14",
            to: "2022-07-14",
        });

        result = getNextDateFilterValue({ type: "relative", period: "last_month" });
        expect(result).toEqual({
            type: "month",
            year: 2022,
            month: 7,
        });

        result = getNextDateFilterValue({ type: "relative", period: "month_to_date" });
        expect(result).toEqual({
            type: "month",
            year: 2022,
            month: 8,
        });
    });

    test("range: shifts range forward", () => {
        expect(
            getNextDateFilterValue({ type: "range", from: "2022-01-01", to: "2022-01-10" })
        ).toEqual({ type: "range", from: "2022-01-11", to: "2022-01-20" });
    });
});

describe("getPreviousDateFilterValue", () => {
    test("month: January rolls back to December previous year", () => {
        expect(getPreviousDateFilterValue({ type: "month", year: 2022, month: 1 })).toEqual({
            type: "month",
            year: 2021,
            month: 12,
        });
    });
    test("month: decrements month", () => {
        expect(getPreviousDateFilterValue({ type: "month", year: 2022, month: 6 })).toEqual({
            type: "month",
            year: 2022,
            month: 5,
        });
    });
    test("quarter: Q1 rolls back to Q4 previous year", () => {
        expect(getPreviousDateFilterValue({ type: "quarter", year: 2022, quarter: 1 })).toEqual({
            type: "quarter",
            year: 2021,
            quarter: 4,
        });
    });
    test("quarter: decrements quarter", () => {
        expect(getPreviousDateFilterValue({ type: "quarter", year: 2022, quarter: 3 })).toEqual({
            type: "quarter",
            year: 2022,
            quarter: 2,
        });
    });
    test("year: decrements year", () => {
        expect(getPreviousDateFilterValue({ type: "year", year: 2022 })).toEqual({
            type: "year",
            year: 2021,
        });
    });

    test("relative", () => {
        mockDate("2022-07-14 00:00:00");

        let result = getPreviousDateFilterValue({ type: "relative", period: "last_7_days" });
        expect(result).toEqual({
            type: "range",
            from: "2022-07-01",
            to: "2022-07-07",
        });

        result = getPreviousDateFilterValue({ type: "relative", period: "last_30_days" });
        expect(result).toEqual({
            type: "range",
            from: "2022-05-16",
            to: "2022-06-14",
        });

        result = getPreviousDateFilterValue({ type: "relative", period: "last_90_days" });
        expect(result).toEqual({
            type: "range",

            from: "2022-01-16",
            to: "2022-04-15",
        });

        result = getPreviousDateFilterValue({ type: "relative", period: "year_to_date" });
        expect(result).toEqual({
            type: "year",
            year: 2021,
        });

        result = getPreviousDateFilterValue({ type: "relative", period: "last_12_months" });
        expect(result).toEqual({
            type: "range",
            from: "2020-07-01",
            to: "2021-06-30",
        });

        result = getPreviousDateFilterValue({ type: "relative", period: "today" });
        expect(result).toEqual({
            type: "range",
            from: "2022-07-13",
            to: "2022-07-13",
        });

        result = getPreviousDateFilterValue({ type: "relative", period: "yesterday" });
        expect(result).toEqual({
            type: "range",
            from: "2022-07-12",
            to: "2022-07-12",
        });

        result = getPreviousDateFilterValue({ type: "relative", period: "last_month" });
        expect(result).toEqual({
            type: "month",
            year: 2022,
            month: 5,
        });

        result = getPreviousDateFilterValue({ type: "relative", period: "month_to_date" });
        expect(result).toEqual({
            type: "month",
            year: 2022,
            month: 6,
        });
    });

    test("range: shifts range backward", () => {
        expect(
            getPreviousDateFilterValue({ type: "range", from: "2022-01-11", to: "2022-01-20" })
        ).toEqual({ type: "range", from: "2022-01-01", to: "2022-01-10" });
    });
});

test("getFacetInfo for boolean values", async () => {
    const filter = {
        type: "boolean",
        label: "Boolean Filter",
        id: "1",
    };
    const env = {};
    expect(await getFacetInfo(env, filter, { operator: "set" })).toEqual({
        title: "Boolean Filter",
        id: "1",
        separator: "or",
        operator: "",
        values: [LAZY_TRANSLATED_SET],
    });
    expect(await getFacetInfo(env, filter, { operator: "not set" })).toEqual({
        title: "Boolean Filter",
        id: "1",
        separator: "or",
        operator: "",
        values: [LAZY_TRANSLATED_NOT_SET],
    });
});

test("getFacetInfo for text values", async () => {
    const filter = {
        type: "text",
        label: "Text Filter",
        id: "1",
    };
    const env = {};
    expect(await getFacetInfo(env, filter, { operator: "ilike", strings: ["hello"] })).toEqual({
        title: "Text Filter",
        id: "1",
        operator: LAZY_TRANSLATED_CONTAINS,
        separator: "or",
        values: ["hello"],
    });
});

test("getFacetInfo for date values", async () => {
    const filter = {
        type: "date",
        label: "Date Filter",
        id: "1",
    };
    const env = {};
    for (const [period, label] of Object.entries(RELATIVE_PERIODS)) {
        expect(await getFacetInfo(env, filter, { type: "relative", period })).toEqual({
            title: "Date Filter",
            id: "1",
            separator: "or",
            operator: "",
            values: [label],
        });
    }
    expect(
        await getFacetInfo(env, filter, { type: "range", from: "2022-01-01", to: "2022-12-31" })
    ).toEqual({
        title: "Date Filter",
        id: "1",
        separator: "or",
        operator: "",
        values: ["January 1 – December 31, 2022"],
    });
    expect(await getFacetInfo(env, filter, { type: "range", from: "2022-01-01" })).toEqual({
        title: "Date Filter",
        id: "1",
        separator: "or",
        operator: "",
        values: ["Since January 1, 2022"],
    });
    expect(await getFacetInfo(env, filter, { type: "range", to: "2022-12-31" })).toEqual({
        title: "Date Filter",
        id: "1",
        separator: "or",
        operator: "",
        values: ["Until December 31, 2022"],
    });
    expect(await getFacetInfo(env, filter, { type: "month", month: 1, year: 2022 })).toEqual({
        title: "Date Filter",
        id: "1",
        separator: "or",
        operator: "",
        values: ["January 2022"],
    });
    expect(await getFacetInfo(env, filter, { type: "quarter", quarter: 1, year: 2022 })).toEqual({
        title: "Date Filter",
        id: "1",
        separator: "or",
        operator: "",
        values: ["Q1 2022"],
    });
    expect(await getFacetInfo(env, filter, { type: "year", year: 2022 })).toEqual({
        title: "Date Filter",
        id: "1",
        separator: "or",
        operator: "",
        values: ["2022"],
    });
});

test("getFacetInfo for relation values", async () => {
    const filter = {
        type: "relation",
        label: "Relation Filter",
        id: "1",
    };
    const nameService = {
        loadDisplayNames: (resModel, ids) => ids.map((id) => `Name ${id}`),
    };
    const env = await makeMockEnv({
        services: {
            name: nameService,
        },
    });
    expect(await getFacetInfo(env, filter, { operator: "in", ids: [1] })).toEqual({
        title: "Relation Filter",
        id: "1",
        separator: "or",
        operator: "",
        values: ["Name 1"],
    });
    expect(await getFacetInfo(env, filter, { operator: "in", ids: [1, 2] })).toEqual({
        title: "Relation Filter",
        id: "1",
        separator: "or",
        operator: "",
        values: ["Name 1", "Name 2"],
    });
});

test("getFacetInfo for selection values", async () => {
    defineSpreadsheetModels();
    const filter = {
        id: "42",
        type: "selection",
        label: "Selection Filter",
        resModel: "res.currency",
        selectionField: "position",
    };
    const env = await makeMockEnv();
    expect(await getFacetInfo(env, filter, { operator: "in", selectionValues: ["after"] })).toEqual(
        {
            title: "Selection Filter",
            id: "42",
            separator: "or",
            operator: "",
            values: ["A"],
        }
    );
    expect(
        await getFacetInfo(env, filter, { operator: "in", selectionValues: ["after", "before"] })
    ).toEqual({
        title: "Selection Filter",
        id: "42",
        separator: "or",
        operator: "",
        values: ["A", "B"],
    });
});
