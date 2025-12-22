import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { mockDate, mockTimeZone } from "@odoo/hoot-mock";
import { patchTranslations, patchWithCleanup } from "@web/../tests/web_test_helpers";

import { Domain } from "@web/core/domain";
import { localization } from "@web/core/l10n/localization";
import { constructDateDomain } from "@web/search/utils/dates";

describe.current.tags("headless");

const dateSearchItem = {
    fieldName: "date_field",
    fieldType: "date",
    optionsParams: {
        customOptions: [],
        endMonth: 0,
        endYear: 0,
        startMonth: -2,
        startYear: -2,
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
    patchTranslations();
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

test(`construct comparison domain based on date field and option "previous_period"`, () => {
    mockDate("2020-01-01T12:00:00");
    const referenceMoment = luxon.DateTime.local();

    let domain = constructDateDomain(
        referenceMoment,
        dateSearchItem,
        ["month", "first_quarter", "year"],
        "previous_period"
    );
    expect(domain).toEqual({
        domain: new Domain(
            "[" +
                `"|",  ` +
                `"&", ("date_field", ">=", "2019-10-01"), ("date_field", "<=", "2019-10-31"), ` +
                `"|", ` +
                `"&", ("date_field", ">=", "2019-11-01"), ("date_field", "<=", "2019-11-30"), ` +
                `"&", ("date_field", ">=", "2019-12-01"), ("date_field", "<=", "2019-12-31")` +
                "]"
        ),
        description: "October 2019/November 2019/December 2019",
    });

    domain = constructDateDomain(
        referenceMoment,
        dateSearchItem,
        ["second_quarter", "year", "year-1"],
        "previous_period"
    );
    expect(domain).toEqual({
        domain: new Domain(
            "[" +
                `"|", ` +
                `"&", ("date_field", ">=", "2018-01-01"), ("date_field", "<=", "2018-03-31"), ` +
                `"&", ("date_field", ">=", "2019-01-01"), ("date_field", "<=", "2019-03-31")` +
                "]"
        ),
        description: "Q1 2018/Q1 2019",
    });

    domain = constructDateDomain(
        referenceMoment,
        dateSearchItem,
        ["year", "year-2", "month", "month-2"],
        "previous_period"
    );
    expect(domain).toEqual({
        domain: new Domain(
            "[" +
                `"|", ` +
                `"&", ("date_field", ">=", "2015-02-01"), ("date_field", "<=", "2015-02-28"), ` +
                `"|", ` +
                `"&", ("date_field", ">=", "2015-12-01"), ("date_field", "<=", "2015-12-31"), ` +
                `"|", ` +
                `"&", ("date_field", ">=", "2017-02-01"), ("date_field", "<=", "2017-02-28"), ` +
                `"&", ("date_field", ">=", "2017-12-01"), ("date_field", "<=", "2017-12-31")` +
                "]"
        ),
        description: "February 2015/December 2015/February 2017/December 2017",
    });

    domain = constructDateDomain(
        referenceMoment,
        dateSearchItem,
        ["year", "year-1"],
        "previous_period"
    );
    expect(domain).toEqual({
        domain: new Domain(
            "[" +
                `"|", ` +
                `"&", ("date_field", ">=", "2017-01-01"), ("date_field", "<=", "2017-12-31"), ` +
                `"&", ("date_field", ">=", "2018-01-01"), ("date_field", "<=", "2018-12-31")` +
                "]"
        ),
        description: "2017/2018",
    });

    domain = constructDateDomain(
        referenceMoment,
        dateSearchItem,
        ["second_quarter", "third_quarter", "year-1"],
        "previous_period"
    );
    expect(domain).toEqual({
        domain: new Domain(
            "[" +
                `"|", ` +
                `"&", ("date_field", ">=", "2018-10-01"), ("date_field", "<=", "2018-12-31"), ` +
                `"&", ("date_field", ">=", "2019-01-01"), ("date_field", "<=", "2019-03-31")` +
                "]"
        ),
        description: "Q4 2018/Q1 2019",
    });
});

test(`construct comparison domain based on datetime field and option "previous_year"`, () => {
    mockDate("2020-06-01T13:00:00");
    const referenceMoment = luxon.DateTime.local();

    let domain = constructDateDomain(
        referenceMoment,
        dateTimeSearchItem,
        ["month", "first_quarter", "year"],
        "previous_year"
    );
    expect(domain).toEqual({
        domain: new Domain(
            "[" +
                `"|", ` +
                `"&", ("date_field", ">=", "2019-06-01 00:00:00"), ("date_field", "<=", "2019-06-30 23:59:59"), ` +
                `"&", ("date_field", ">=", "2019-01-01 00:00:00"), ("date_field", "<=", "2019-03-31 23:59:59")` +
                "]"
        ),
        description: "June 2019/Q1 2019",
    });

    domain = constructDateDomain(
        referenceMoment,
        dateTimeSearchItem,
        ["second_quarter", "year", "year-1"],
        "previous_year"
    );
    expect(domain).toEqual({
        domain: new Domain(
            "[" +
                `"|", ` +
                `"&", ("date_field", ">=", "2018-04-01 00:00:00"), ("date_field", "<=", "2018-06-30 23:59:59"), ` +
                `"&", ("date_field", ">=", "2019-04-01 00:00:00"), ("date_field", "<=", "2019-06-30 23:59:59")` +
                "]"
        ),
        description: "Q2 2018/Q2 2019",
    });

    domain = constructDateDomain(
        referenceMoment,
        dateTimeSearchItem,
        ["year", "year-2", "month", "month-2"],
        "previous_year"
    );
    expect(domain).toEqual({
        domain: new Domain(
            "[" +
                `"|", ` +
                `"&", ("date_field", ">=", "2017-04-01 00:00:00"), ("date_field", "<=", "2017-04-30 23:59:59"), ` +
                `"|", ` +
                `"&", ("date_field", ">=", "2017-06-01 00:00:00"), ("date_field", "<=", "2017-06-30 23:59:59"), ` +
                `"|", ` +
                `"&", ("date_field", ">=", "2019-04-01 00:00:00"), ("date_field", "<=", "2019-04-30 23:59:59"), ` +
                `"&", ("date_field", ">=", "2019-06-01 00:00:00"), ("date_field", "<=", "2019-06-30 23:59:59")` +
                "]"
        ),
        description: "April 2017/June 2017/April 2019/June 2019",
    });
});

test("Quarter option: custom translation", async () => {
    mockDate("2020-06-01T13:00:00");
    const referenceMoment = luxon.DateTime.local().setLocale("en");
    patchTranslations({ Q2: "Deuxième trimestre de l'an de grâce" });

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
    patchTranslations({ Q2: "2e Trimestre" });

    const domain = constructDateDomain(referenceMoment, dateSearchItem, ["second_quarter", "year"]);
    expect(domain).toEqual({
        domain: new Domain(
            `["&", ("date_field", ">=", "2020-04-01"), ("date_field", "<=", "2020-06-30")]`
        ),
        description: "2020 2e Trimestre",
    });
});
