import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { mockDate, mockTimeZone } from "@odoo/hoot-mock";
import {
    allowTranslations,
    patchTranslations,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";

import { Domain } from "@web/core/domain";
import { localization } from "@web/core/l10n/localization";
import {
    constructDateDomain,
    getRelativeDateLabel,
    RELATIVE_FILTER_OPTIONS,
} from "@web/search/utils/dates";

describe.current.tags("headless");

const dateSearchItem = {
    fieldName: "date_field",
    fieldType: "date",
    optionsParams: {
        customOptions: [],
    },
    type: "dateFilter",
};
const dateTimeSearchItem = {
    ...dateSearchItem,
    fieldType: "datetime",
};

beforeEach(() => {
    mockTimeZone(0);
    patchWithCleanup(localization, { direction: "ltr" });
    allowTranslations();
});

test("construct simple domain based on date field (no comparisonOptionId)", () => {
    mockDate("2020-06-01T13:00:00");
    const referenceMoment = luxon.DateTime.local();

    let domain = constructDateDomain(referenceMoment, dateSearchItem, []);
    expect(domain).toEqual({
        domain: new Domain(`[]`),
        description: "",
    });

    domain = constructDateDomain(referenceMoment, dateSearchItem, ["month", "year"]);
    expect(domain).toEqual({
        domain: new Domain(
            `["&", ("date_field", ">=", "2020-06-01"), ("date_field", "<=", "2020-06-30")]`
        ),
        description: "June 2020",
    });

    domain = constructDateDomain(referenceMoment, dateSearchItem, ["second_quarter", "year"]);
    expect(domain).toEqual({
        domain: new Domain(
            `["&", ("date_field", ">=", "2020-04-01"), ("date_field", "<=", "2020-06-30")]`
        ),
        description: "Q2 2020",
    });

    domain = constructDateDomain(referenceMoment, dateSearchItem, ["year"]);
    expect(domain).toEqual({
        domain: new Domain(
            `["&", ("date_field", ">=", "2020-01-01"), ("date_field", "<=", "2020-12-31")]`
        ),
        description: "2020",
    });
});

test("construct simple domain based on date field (no comparisonOptionId) - UTC+2", () => {
    mockTimeZone(2);
    mockDate("2020-06-01T00:00:00");
    const referenceMoment = luxon.DateTime.local();

    let domain = constructDateDomain(referenceMoment, dateSearchItem, []);
    expect(domain).toEqual({
        domain: new Domain(`[]`),
        description: "",
    });

    domain = constructDateDomain(referenceMoment, dateSearchItem, ["month", "year"]);
    expect(domain).toEqual({
        domain: new Domain(
            `["&", ("date_field", ">=", "2020-06-01"), ("date_field", "<=", "2020-06-30")]`
        ),
        description: "June 2020",
    });

    domain = constructDateDomain(referenceMoment, dateSearchItem, ["second_quarter", "year"]);
    expect(domain).toEqual({
        domain: new Domain(
            `["&", ("date_field", ">=", "2020-04-01"), ("date_field", "<=", "2020-06-30")]`
        ),
        description: "Q2 2020",
    });

    domain = constructDateDomain(referenceMoment, dateSearchItem, ["year"]);
    expect(domain).toEqual({
        domain: new Domain(
            `["&", ("date_field", ">=", "2020-01-01"), ("date_field", "<=", "2020-12-31")]`
        ),
        description: "2020",
    });
});

test("construct simple domain based on datetime field (no comparisonOptionId)", () => {
    mockDate("2020-06-01T13:00:00");
    const referenceMoment = luxon.DateTime.local();

    let domain = constructDateDomain(referenceMoment, dateTimeSearchItem, ["month", "year"]);
    expect(domain).toEqual({
        domain: new Domain(
            `["&", ("date_field", ">=", "2020-06-01 00:00:00"), ("date_field", "<=", "2020-06-30 23:59:59")]`
        ),
        description: "June 2020",
    });

    domain = constructDateDomain(referenceMoment, dateTimeSearchItem, ["second_quarter", "year"]);
    expect(domain).toEqual({
        domain: new Domain(
            `["&", ("date_field", ">=", "2020-04-01 00:00:00"), ("date_field", "<=", "2020-06-30 23:59:59")]`
        ),
        description: "Q2 2020",
    });

    domain = constructDateDomain(referenceMoment, dateTimeSearchItem, ["year"]);
    expect(domain).toEqual({
        domain: new Domain(
            `["&", ("date_field", ">=", "2020-01-01 00:00:00"), ("date_field", "<=", "2020-12-31 23:59:59")]`
        ),
        description: "2020",
    });
});

test("construct simple domain based on datetime field (no comparisonOptionId) - UTC+2", () => {
    mockTimeZone(2);
    mockDate("2020-06-01T00:00:00");
    const referenceMoment = luxon.DateTime.local();

    let domain = constructDateDomain(referenceMoment, dateTimeSearchItem, ["month", "year"]);
    expect(domain).toEqual({
        domain: new Domain(
            `["&", ("date_field", ">=", "2020-05-31 22:00:00"), ("date_field", "<=", "2020-06-30 21:59:59")]`
        ),
        description: "June 2020",
    });

    domain = constructDateDomain(referenceMoment, dateTimeSearchItem, ["second_quarter", "year"]);
    expect(domain).toEqual({
        domain: new Domain(
            `["&", ("date_field", ">=", "2020-03-31 22:00:00"), ("date_field", "<=", "2020-06-30 21:59:59")]`
        ),
        description: "Q2 2020",
    });

    domain = constructDateDomain(referenceMoment, dateTimeSearchItem, ["year"]);
    expect(domain).toEqual({
        domain: new Domain(
            `["&", ("date_field", ">=", "2019-12-31 22:00:00"), ("date_field", "<=", "2020-12-31 21:59:59")]`
        ),
        description: "2020",
    });
});

test("construct domain based on date field (no comparisonOptionId)", () => {
    mockDate("2020-01-01T12:00:00");
    const referenceMoment = luxon.DateTime.local();

    let domain = constructDateDomain(referenceMoment, dateSearchItem, [
        "month",
        "first_quarter",
        "year",
    ]);
    expect(domain).toEqual({
        domain: new Domain(
            "[" +
                `"|", ` +
                `"&", ("date_field", ">=", "2020-01-01"), ("date_field", "<=", "2020-01-31"), ` +
                `"&", ("date_field", ">=", "2020-01-01"), ("date_field", "<=", "2020-03-31")` +
                "]"
        ),
        description: "January 2020/Q1 2020",
    });

    domain = constructDateDomain(referenceMoment, dateSearchItem, [
        "second_quarter",
        "year",
        "year-1",
    ]);
    expect(domain).toEqual({
        domain: new Domain(
            "[" +
                `"|", ` +
                `"&", ("date_field", ">=", "2019-04-01"), ("date_field", "<=", "2019-06-30"), ` +
                `"&", ("date_field", ">=", "2020-04-01"), ("date_field", "<=", "2020-06-30")` +
                "]"
        ),
        description: "Q2 2019/Q2 2020",
    });

    domain = constructDateDomain(referenceMoment, dateSearchItem, ["year", "month", "month-2"]);
    expect(domain).toEqual({
        domain: new Domain(
            "[" +
                `"|", ` +
                `"&", ("date_field", ">=", "2020-01-01"), ("date_field", "<=", "2020-01-31"), ` +
                `"&", ("date_field", ">=", "2020-11-01"), ("date_field", "<=", "2020-11-30")` +
                "]"
        ),
        description: "January 2020/November 2020",
    });
});

test("construct domain based on datetime field (no comparisonOptionId)", () => {
    mockDate("2020-01-01T12:00:00");
    const referenceMoment = luxon.DateTime.local();

    let domain = constructDateDomain(referenceMoment, dateTimeSearchItem, [
        "month",
        "first_quarter",
        "year",
    ]);
    expect(domain).toEqual({
        domain: new Domain(
            "[" +
                `"|", ` +
                `"&", ("date_field", ">=", "2020-01-01 00:00:00"), ("date_field", "<=", "2020-01-31 23:59:59"), ` +
                `"&", ("date_field", ">=", "2020-01-01 00:00:00"), ("date_field", "<=", "2020-03-31 23:59:59")` +
                "]"
        ),
        description: "January 2020/Q1 2020",
    });

    domain = constructDateDomain(referenceMoment, dateTimeSearchItem, [
        "second_quarter",
        "year",
        "year-1",
    ]);
    expect(domain).toEqual({
        domain: new Domain(
            "[" +
                `"|", ` +
                `"&", ("date_field", ">=", "2019-04-01 00:00:00"), ("date_field", "<=", "2019-06-30 23:59:59"), ` +
                `"&", ("date_field", ">=", "2020-04-01 00:00:00"), ("date_field", "<=", "2020-06-30 23:59:59")` +
                "]"
        ),
        description: "Q2 2019/Q2 2020",
    });

    domain = constructDateDomain(referenceMoment, dateTimeSearchItem, ["year", "month", "month-2"]);
    expect(domain).toEqual({
        domain: new Domain(
            "[" +
                `"|", ` +
                `"&", ("date_field", ">=", "2020-01-01 00:00:00"), ("date_field", "<=", "2020-01-31 23:59:59"), ` +
                `"&", ("date_field", ">=", "2020-11-01 00:00:00"), ("date_field", "<=", "2020-11-30 23:59:59")` +
                "]"
        ),
        description: "January 2020/November 2020",
    });
});

test("Quarter option: custom translation", async () => {
    mockDate("2020-06-01T13:00:00");
    const referenceMoment = luxon.DateTime.local().setLocale("en");
    patchTranslations({ web: { Q2: "Deuxième trimestre de l'an de grâce" } });

    const domain = constructDateDomain(referenceMoment, dateSearchItem, ["second_quarter", "year"]);
    expect(domain).toEqual({
        domain: new Domain(
            `["&", ("date_field", ">=", "2020-04-01"), ("date_field", "<=", "2020-06-30")]`
        ),
        description: "Deuxième trimestre de l'an de grâce 2020",
    });
});

test("Quarter option: right to left", async () => {
    mockDate("2020-06-01T13:00:00");
    const referenceMoment = luxon.DateTime.local().setLocale("en");
    patchWithCleanup(localization, { direction: "rtl" });

    const domain = constructDateDomain(referenceMoment, dateSearchItem, ["second_quarter", "year"]);
    expect(domain).toEqual({
        domain: new Domain(
            `["&", ("date_field", ">=", "2020-04-01"), ("date_field", "<=", "2020-06-30")]`
        ),
        description: "2020 Q2",
    });
});

test("Quarter option: custom translation and right to left", async () => {
    mockDate("2020-06-01T13:00:00");
    const referenceMoment = luxon.DateTime.local().setLocale("en");
    patchWithCleanup(localization, { direction: "rtl" });
    patchTranslations({ web: { Q2: "2e Trimestre" } });

    const domain = constructDateDomain(referenceMoment, dateSearchItem, ["second_quarter", "year"]);
    expect(domain).toEqual({
        domain: new Domain(
            `["&", ("date_field", ">=", "2020-04-01"), ("date_field", "<=", "2020-06-30")]`
        ),
        description: "2020 2e Trimestre",
    });
});

test("relative filter labels: the period covered, current year left implicit", () => {
    mockDate("2026-08-07T13:00:00"); // Friday
    patchWithCleanup(localization, { weekStart: 7 }); // Sunday
    const referenceMoment = luxon.DateTime.local().setLocale("en");
    const label = (optionId, offset) =>
        getRelativeDateLabel(referenceMoment, RELATIVE_FILTER_OPTIONS[optionId], offset);

    expect(label("today", 0)).toBe("Aug 7");
    expect(label("today", -1)).toBe("Aug 6");
    expect(label("today", 2)).toBe("Aug 9");

    expect(label("this_week", 0)).toBe("Week 32, Aug 2 - Aug 8");
    expect(label("this_week", -1)).toBe("Week 31, Jul 26 - Aug 1");

    expect(label("this_month", 0)).toBe("August");
    expect(label("this_month", -2)).toBe("June");

    expect(label("this_quarter", 0)).toBe("Q3");
    expect(label("this_quarter", -1)).toBe("Q2");

    expect(label("this_year", 0)).toBe("2026");
});

test("relative filter labels: the year shows up as soon as we leave the current one", () => {
    mockDate("2026-08-07T13:00:00"); // Friday
    patchWithCleanup(localization, { weekStart: 7 }); // Sunday
    const referenceMoment = luxon.DateTime.local().setLocale("en");
    const label = (optionId, offset) =>
        getRelativeDateLabel(referenceMoment, RELATIVE_FILTER_OPTIONS[optionId], offset);

    expect(label("today", -220)).toBe("Dec 30, 2025");
    expect(label("this_week", 21)).toBe("Week 53, Dec 27 - Jan 2"); // still a week of 2026
    expect(label("this_week", 30)).toBe("Week 9, Feb 28 - Mar 6 2027");
    expect(label("this_month", 5)).toBe("January 2027");
    expect(label("this_quarter", 2)).toBe("Q1 2027");
    expect(label("this_year", -1)).toBe("2025");
});

test("relative filter labels: digits follow the active numbering system", () => {
    mockDate("2026-08-07T13:00:00"); // Friday
    patchWithCleanup(localization, { weekStart: 7 }); // Sunday
    patchWithCleanup(luxon.Settings, { defaultNumberingSystem: "arab" });
    const referenceMoment = luxon.DateTime.local().setLocale("en");
    const label = (optionId, offset) =>
        getRelativeDateLabel(referenceMoment, RELATIVE_FILTER_OPTIONS[optionId], offset);

    expect(label("today", 0)).toBe("Aug ٧");
    expect(label("this_week", 0)).toBe("Week ٣٢, Aug ٢ - Aug ٨");
    expect(label("this_month", 0)).toBe("August");
    expect(label("this_year", 0)).toBe("٢٠٢٦");

    // and the year, wherever it shows up, uses them too
    expect(label("this_month", 5)).toBe("January ٢٠٢٧");
    expect(label("this_quarter", 2)).toBe("Q1 ٢٠٢٧");
    expect(label("this_year", -1)).toBe("٢٠٢٥");
});

test("relative filter labels: quarter of another year, right to left", () => {
    mockDate("2026-08-07T13:00:00");
    patchWithCleanup(localization, { direction: "rtl" });
    const referenceMoment = luxon.DateTime.local().setLocale("en");

    const label = (offset) =>
        getRelativeDateLabel(referenceMoment, RELATIVE_FILTER_OPTIONS.this_quarter, offset);
    expect(label(0)).toBe("Q3");
    expect(label(2)).toBe("2027 Q1");
});
