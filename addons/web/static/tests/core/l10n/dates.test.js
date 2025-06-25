import { beforeEach, expect, test } from "@odoo/hoot";
import { mockDate, mockTimeZone } from "@odoo/hoot-mock";
import {
    defineParams,
    makeMockEnv,
    patchTranslations,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";

import {
    deserializeDate,
    deserializeDateTime,
    formatDate,
    formatDateTime,
    parseDate,
    parseDateTime,
    serializeDate,
    serializeDateTime,
    strftimeToLuxonFormat,
} from "@web/core/l10n/dates";
import { localization } from "@web/core/l10n/localization";

const { DateTime, Settings } = luxon;

const formats = {
    date: "%d.%m/%Y",
    time: "%H:%M:%S",
};
const dateFormat = strftimeToLuxonFormat(formats.date);
const timeFormat = strftimeToLuxonFormat(formats.time);

beforeEach(() => {
    patchTranslations();
});

test("formatDate/formatDateTime specs", async () => {
    patchWithCleanup(localization, {
        dateFormat: "MM/dd/yyyy",
        dateTimeFormat: "MM/dd/yyyy HH:mm:ss",
    });
    mockDate("2009-05-04 11:34:56", +1);

    const utc = DateTime.utc(); // 2009-05-04T11:34:56.000Z
    const local = DateTime.local(); // 2009-05-04T12:34:56.000+01:00
    const minus13FromLocalTZ = local.setZone("UTC-12"); // 2009-05-03T23:34:56.000-12:00

    // For dates, regardless of the input timezone, outputs only the date
    expect(formatDate(utc)).toBe("05/04/2009");
    expect(formatDate(local)).toBe("05/04/2009");
    expect(formatDate(minus13FromLocalTZ)).toBe("05/03/2009");

    // For datetimes, input timezone is taken into account, outputs in local timezone
    expect(formatDateTime(utc)).toBe("05/04/2009 12:34:56");
    expect(formatDateTime(local)).toBe("05/04/2009 12:34:56");
    expect(formatDateTime(minus13FromLocalTZ)).toBe("05/04/2009 12:34:56");
});

test("formatDate/formatDateTime specs, at midnight", async () => {
    patchWithCleanup(localization, {
        dateFormat: "MM/dd/yyyy",
        dateTimeFormat: "MM/dd/yyyy HH:mm:ss",
    });
    mockDate("2009-05-03 23:00:00", +1);

    const utc = DateTime.utc(); // 2009-05-03T23:00:00.000Z
    const local = DateTime.local(); // 2009-05-04T00:00:00.000+01:00
    const minus13FromLocalTZ = local.setZone("UTC-12"); // 2009-05-03T11:00:00.000-12:00

    // For dates, regardless of the input timezone, outputs only the date
    expect(formatDate(utc)).toBe("05/03/2009");
    expect(formatDate(local)).toBe("05/04/2009");
    expect(formatDate(minus13FromLocalTZ)).toBe("05/03/2009");

    // For datetimes, input timezone is taken into account, outputs in local timezone
    expect(formatDateTime(utc)).toBe("05/04/2009 00:00:00");
    expect(formatDateTime(local)).toBe("05/04/2009 00:00:00");
    expect(formatDateTime(minus13FromLocalTZ)).toBe("05/04/2009 00:00:00");
});

test("formatDate/formatDateTime with condensed option", async () => {
    mockDate("2009-05-03 08:00:00");
    mockTimeZone(0);
    const now = DateTime.now();

    patchWithCleanup(localization, {
        dateFormat: "MM/dd/yyyy",
        dateTimeFormat: "MM/dd/yyyy HH:mm:ss",
    });
    expect(formatDate(now, { condensed: true })).toBe("5/3/2009");
    expect(formatDateTime(now, { condensed: true })).toBe("5/3/2009 8:00:00");

    patchWithCleanup(localization, { dateFormat: "yyyy-MM-dd" });
    expect(formatDate(now, { condensed: true })).toBe("2009-5-3");

    patchWithCleanup(localization, { dateFormat: "dd MMM yy" });
    expect(formatDate(now, { condensed: true })).toBe("3 May 09");
});

test("formatDateTime in different timezone", async () => {
    patchWithCleanup(localization, {
        dateFormat: "MM/dd/yyyy",
        dateTimeFormat: "MM/dd/yyyy HH:mm:ss",
    });
    mockDate("2009-05-04 00:00:00", 0);
    expect(formatDateTime(DateTime.utc())).toBe("05/04/2009 00:00:00");
    expect(formatDateTime(DateTime.utc(), { tz: "Asia/Kolkata" })).toBe("05/04/2009 05:30:00");
});

test("parseDate(Time) outputs DateTime objects in local TZ", async () => {
    await makeMockEnv();
    mockTimeZone(+1);
    expect(parseDate("01/13/2019").toISO()).toBe("2019-01-13T00:00:00.000+01:00");
    expect(parseDateTime("01/13/2019 10:05:45").toISO()).toBe("2019-01-13T10:05:45.000+01:00");

    mockTimeZone(+5.5);
    expect(parseDate("01/13/2019").toISO()).toBe("2019-01-13T00:00:00.000+05:30");
    expect(parseDateTime("01/13/2019 10:05:45").toISO()).toBe("2019-01-13T10:05:45.000+05:30");

    mockTimeZone(-11);
    expect(parseDate("01/13/2019").toISO()).toBe("2019-01-13T00:00:00.000-11:00");
    expect(parseDateTime("01/13/2019 10:05:45").toISO()).toBe("2019-01-13T10:05:45.000-11:00");
});

test("parseDateTime in different timezone", async () => {
    await makeMockEnv();
    mockTimeZone(+1);
    expect(parseDateTime("01/13/2019 10:05:45").toISO()).toBe("2019-01-13T10:05:45.000+01:00");
    expect(parseDateTime("01/13/2019 10:05:45", { tz: "Asia/Kolkata" }).toISO()).toBe(
        "2019-01-13T10:05:45.000+05:30"
    );
});

test("parseDate with different numbering system", async () => {
    patchWithCleanup(localization, {
        dateFormat: "dd MMM, yyyy",
        dateTimeFormat: "dd MMM, yyyy hh:mm:ss",
        timeFormat: "hh:mm:ss",
    });

    patchWithCleanup(Settings, { defaultNumberingSystem: "arab", defaultLocale: "ar" });

    expect(parseDate("٠١ فبراير, ٢٠٢٣").toISO()).toBe("2023-02-01T00:00:00.000+01:00");
});

test("parseDateTime", async () => {
    expect(() => parseDateTime("13/01/2019 12:00:00")).toThrow(/is not a correct/, {
        message: "Wrongly formated dates should be invalid",
    });
    expect(() => parseDateTime("01/01/0999 12:00:00")).toThrow(/is not a correct/, {
        message: "Dates before 1000 should be invalid",
    });
    expect(() => parseDateTime("01/01/10000 12:00:00")).toThrow(/is not a correct/, {
        message: "Dates after 9999 should be invalid",
    });
    expect(() => parseDateTime("invalid value")).toThrow(/is not a correct/);

    const expected = "2019-01-13T10:05:45.000+01:00";
    expect(parseDateTime("01/13/2019 10:05:45").toISO()).toBe(expected, {
        message: "Date with leading 0",
    });
    expect(parseDateTime("1/13/2019 10:5:45").toISO()).toBe(expected, {
        message: "Date without leading 0",
    });
});

test("parseDateTime (norwegian locale)", async () => {
    defineParams({
        lang: "no", // Norwegian
        lang_parameters: {
            date_format: "%d. %b %Y",
            time_format: "%H:%M:%S",
        },
    });
    await makeMockEnv();

    expect(parseDateTime("16. des 2019 10:05:45").toISO()).toBe("2019-12-16T10:05:45.000+01:00", {
        message: "Day/month inverted + month i18n",
    });
});

test("parseDate", async () => {
    await makeMockEnv();
    expect(parseDate("07/21/2022").toISO()).toBe("2022-07-21T00:00:00.000+01:00");
    expect(parseDate("07/22/2022").toISO()).toBe("2022-07-22T00:00:00.000+01:00");
});

test("parseDate without separator", async () => {
    const dateFormat = strftimeToLuxonFormat("%d.%m/%Y");
    const timeFormat = strftimeToLuxonFormat("%H:%M:%S");
    patchWithCleanup(localization, {
        dateFormat,
        timeFormat,
        dateTimeFormat: `${dateFormat} ${timeFormat}`,
    });

    const testDateFormat = "dd.MM/yyyy";

    expect(() => parseDate("1137")).toThrow(/is not a correct/, {
        message: "Wrongly formated dates should be invalid",
    });
    expect(() => parseDate("1197")).toThrow(/is not a correct/, {
        message: "Wrongly formated dates should be invalid",
    });
    expect(() => parseDate("0131")).toThrow(/is not a correct/, {
        message: "Wrongly formated dates should be invalid",
    });
    expect(() => parseDate("970131")).toThrow(/is not a correct/, {
        message: "Wrongly formated dates should be invalid",
    });
    expect(parseDate("2001").toFormat(testDateFormat)).toBe("20.01/" + DateTime.utc().year);
    expect(parseDate("3101").toFormat(testDateFormat)).toBe("31.01/" + DateTime.utc().year);
    expect(parseDate("31.01").toFormat(testDateFormat)).toBe("31.01/" + DateTime.utc().year);
    expect(parseDate("310197").toFormat(testDateFormat)).toBe("31.01/1997");
    expect(parseDate("310117").toFormat(testDateFormat)).toBe("31.01/2017");
    expect(parseDate("31011985").toFormat(testDateFormat)).toBe("31.01/1985");
});

test("parseDateTime without separator", async () => {
    const dateFormat = strftimeToLuxonFormat("%d.%m/%Y");
    const timeFormat = strftimeToLuxonFormat("%H:%M:%S");
    patchWithCleanup(localization, {
        dateFormat,
        timeFormat,
        dateTimeFormat: `${dateFormat} ${timeFormat}`,
    });

    const dateTimeFormat = "dd.MM/yyyy HH:mm/ss";
    expect(parseDateTime("3101198508").toFormat(dateTimeFormat)).toBe("31.01/1985 08:00/00");
    expect(parseDateTime("310119850833").toFormat(dateTimeFormat)).toBe("31.01/1985 08:33/00");
    expect(parseDateTime("31/01/1985 08").toFormat(dateTimeFormat)).toBe("31.01/1985 08:00/00");
});

test("parseDateTime with escaped characters (eg. Basque locale)", async () => {
    const dateFormat = strftimeToLuxonFormat("%a, %Y.eko %bren %da");
    const timeFormat = strftimeToLuxonFormat("%H:%M:%S");
    patchWithCleanup(localization, {
        dateFormat,
        timeFormat,
        dateTimeFormat: `${dateFormat} ${timeFormat}`,
    });

    const dateTimeFormat = `${dateFormat} ${timeFormat}`;
    expect(dateTimeFormat).toBe("ccc, yyyy.'e''k''o' MMM'r''e''n' dd'a' HH:mm:ss");
    expect(parseDateTime("1985-01-31 08:30:00").toFormat(dateTimeFormat)).toBe(
        "Thu, 1985.eko Janren 31a 08:30:00"
    );
});

test("parse smart date input", async () => {
    mockDate("2020-01-01 00:00:00", 0);

    const format = "yyyy-MM-dd HH:mm";
    // with parseDate
    expect(parseDate("+0").toFormat(format)).toBe("2020-01-01 00:00");
    expect(parseDate("-0").toFormat(format)).toBe("2020-01-01 00:00");
    expect(parseDate("+1d").toFormat(format)).toBe("2020-01-02 00:00");
    expect(parseDate("+2w").toFormat(format)).toBe("2020-01-15 00:00");
    expect(parseDate("+3m").toFormat(format)).toBe("2020-04-01 00:00");
    expect(parseDate("+4y").toFormat(format)).toBe("2024-01-01 00:00");
    expect(parseDate("+5").toFormat(format)).toBe("2020-01-06 00:00");
    expect(parseDate("-5").toFormat(format)).toBe("2019-12-27 00:00");
    expect(parseDate("-4y").toFormat(format)).toBe("2016-01-01 00:00");
    expect(parseDate("-3m").toFormat(format)).toBe("2019-10-01 00:00");
    expect(parseDate("-2w").toFormat(format)).toBe("2019-12-18 00:00");
    expect(parseDate("-1d").toFormat(format)).toBe("2019-12-31 00:00");
    // with parseDateTime
    expect(parseDateTime("+0").toFormat(format)).toBe("2020-01-01 00:00");
    expect(parseDateTime("-0").toFormat(format)).toBe("2020-01-01 00:00");
    expect(parseDateTime("+1d").toFormat(format)).toBe("2020-01-02 00:00");
    expect(parseDateTime("+2w").toFormat(format)).toBe("2020-01-15 00:00");
    expect(parseDateTime("+3m").toFormat(format)).toBe("2020-04-01 00:00");
    expect(parseDateTime("+4y").toFormat(format)).toBe("2024-01-01 00:00");
    expect(parseDateTime("+5").toFormat(format)).toBe("2020-01-06 00:00");
    expect(parseDateTime("-5").toFormat(format)).toBe("2019-12-27 00:00");
    expect(parseDateTime("-4y").toFormat(format)).toBe("2016-01-01 00:00");
    expect(parseDateTime("-3m").toFormat(format)).toBe("2019-10-01 00:00");
    expect(parseDateTime("-2w").toFormat(format)).toBe("2019-12-18 00:00");
    expect(parseDateTime("-1d").toFormat(format)).toBe("2019-12-31 00:00");
});

test("parseDateTime ISO8601 Format", async () => {
    mockTimeZone(+1);
    expect(parseDateTime("2017-05-15T12:00:00.000+06:00").toISO()).toBe(
        "2017-05-15T07:00:00.000+01:00"
    );
    // without the 'T' separator is not really ISO8601 compliant, but we still support it
    expect(parseDateTime("2017-05-15 12:00:00.000+06:00").toISO()).toBe(
        "2017-05-15T07:00:00.000+01:00"
    );
});

test("parseDateTime SQL Format", async () => {
    expect(parseDateTime("2017-05-15 09:12:34").toISO()).toBe("2017-05-15T09:12:34.000+01:00");
    expect(parseDateTime("2017-05-08 09:12:34").toISO()).toBe("2017-05-08T09:12:34.000+01:00");
});

test("serializeDate", async () => {
    const date = DateTime.utc(2022, 2, 21, 16, 11, 42);
    expect(date.toFormat("yyyy-MM-dd")).toBe("2022-02-21");
    expect(serializeDate(date)).toBe("2022-02-21");
});

test("serializeDate, with DateTime.now()", async () => {
    mockDate("2022-02-21 15:11:42");
    const date = DateTime.now();
    expect(date.toFormat("yyyy-MM-dd")).toBe("2022-02-21");
    expect(serializeDate(date)).toBe("2022-02-21");
});

test("serializeDate, with DateTime.now(), midnight", async () => {
    mockDate("2022-02-20 23:00:00");
    const date = DateTime.now();
    expect(date.toFormat("yyyy-MM-dd")).toBe("2022-02-21");
    expect(serializeDate(date)).toBe("2022-02-21");
});

test("serializeDate with different numbering system", async () => {
    patchWithCleanup(Settings, { defaultNumberingSystem: "arab" });
    const date = DateTime.utc(2022, 2, 21, 16, 11, 42);
    expect(date.toFormat("yyyy-MM-dd")).toBe("٢٠٢٢-٠٢-٢١");
    expect(serializeDate(date)).toBe("2022-02-21");
});

test("serializeDateTime", async () => {
    const date = DateTime.utc(2022, 2, 21, 16, 11, 42);
    expect(date.toFormat("yyyy-MM-dd HH:mm:ss")).toBe("2022-02-21 16:11:42");
    expect(serializeDateTime(date)).toBe("2022-02-21 16:11:42");
});

test("serializeDateTime, with DateTime.now()", async () => {
    mockDate("2022-02-21 15:11:42");
    const date = DateTime.now();
    expect(date.toFormat("yyyy-MM-dd HH:mm:ss")).toBe("2022-02-21 16:11:42");
    expect(serializeDateTime(date)).toBe("2022-02-21 15:11:42");
});

test("serializeDateTime, with DateTime.now(), midnight", async () => {
    mockDate("2022-02-20 23:00:00");
    const date = DateTime.now();
    expect(date.toFormat("yyyy-MM-dd HH:mm:ss")).toBe("2022-02-21 00:00:00");
    expect(serializeDateTime(date)).toBe("2022-02-20 23:00:00");
});

test("serializeDateTime with different numbering system", async () => {
    patchWithCleanup(Settings, { defaultNumberingSystem: "arab" });
    const date = DateTime.utc(2022, 2, 21, 16, 11, 42);
    expect(date.toFormat("yyyy-MM-dd HH:mm:ss")).toBe("٢٠٢٢-٠٢-٢١ ١٦:١١:٤٢");
    expect(serializeDateTime(date)).toBe("2022-02-21 16:11:42");
});

test("deserializeDate", async () => {
    const date = DateTime.local(2022, 2, 21);
    expect(DateTime.fromFormat("2022-02-21", "yyyy-MM-dd").toMillis()).toBe(date.toMillis());
    expect(deserializeDate("2022-02-21").toMillis()).toBe(date.toMillis());
});

test("deserializeDate with different numbering system", async () => {
    patchWithCleanup(Settings, { defaultNumberingSystem: "arab" });
    const date = DateTime.local(2022, 2, 21);
    expect(DateTime.fromFormat("٢٠٢٢-٠٢-٢١", "yyyy-MM-dd").toMillis()).toBe(date.toMillis());
    expect(deserializeDate("2022-02-21").toMillis()).toBe(date.toMillis());
});

test("deserializeDateTime", async () => {
    const date = DateTime.utc(2022, 2, 21, 16, 11, 42);
    expect(
        DateTime.fromFormat("2022-02-21 16:11:42", "yyyy-MM-dd HH:mm:ss", {
            zone: "utc",
        }).toMillis()
    ).toBe(date.toMillis());
    expect(deserializeDateTime("2022-02-21 16:11:42").toMillis()).toBe(date.toMillis());
});

test("deserializeDateTime with different numbering system", async () => {
    patchWithCleanup(Settings, { defaultNumberingSystem: "arab" });
    const date = DateTime.utc(2022, 2, 21, 16, 11, 42);
    expect(
        DateTime.fromFormat("٢٠٢٢-٠٢-٢١ ١٦:١١:٤٢", "yyyy-MM-dd HH:mm:ss", {
            zone: "utc",
        }).toMillis()
    ).toBe(date.toMillis());
    expect(deserializeDateTime("2022-02-21 16:11:42").toMillis()).toBe(date.toMillis());
});

test("deserializeDateTime with different timezone", async () => {
    const date = DateTime.utc(2022, 2, 21, 16, 11, 42).setZone("Europe/Brussels");
    expect(deserializeDateTime("2022-02-21 16:11:42", { tz: "Europe/Brussels" }).c).toEqual(date.c);
});

test("parseDate with short notations", async () => {
    expect(parseDate("20-10-20", { format: "yyyy-MM-dd" }).toISO()).toBe(
        "2020-10-20T00:00:00.000+01:00"
    );
    expect(parseDate("20/10/20", { format: "yyyy/MM/dd" }).toISO()).toBe(
        "2020-10-20T00:00:00.000+01:00"
    );
    expect(parseDate("10-20-20", { format: "MM-dd-yyyy" }).toISO()).toBe(
        "2020-10-20T00:00:00.000+01:00"
    );
    expect(parseDate("10-20-20", { format: "MM-yyyy-dd" }).toISO()).toBe(
        "2020-10-20T00:00:00.000+01:00"
    );
    expect(parseDate("1-20-2", { format: "MM-yyyy-dd" }).toISO()).toBe(
        "2020-01-02T00:00:00.000+01:00"
    );
    expect(parseDate("20/1/2", { format: "yyyy/MM/dd" }).toISO()).toBe(
        "2020-01-02T00:00:00.000+01:00"
    );
});

test("parseDateTime with short notations", async () => {
    expect(parseDateTime("20-10-20 8:5:3", { format: "yyyy-MM-dd hh:mm:ss" }).toISO()).toBe(
        "2020-10-20T08:05:03.000+01:00"
    );
});

test("parseDate with textual month notation", async () => {
    patchWithCleanup(localization, {
        dateFormat: "MMM/dd/yyyy",
    });
    expect(parseDate("Jan/05/1997").toISO()).toBe("1997-01-05T00:00:00.000+01:00");
    expect(parseDate("Jan/05/1997", { format: undefined }).toISO()).toBe(
        "1997-01-05T00:00:00.000+01:00"
    );
    expect(parseDate("Jan/05/1997", { format: "MMM/dd/yyyy" }).toISO()).toBe(
        "1997-01-05T00:00:00.000+01:00"
    );
});

test("parseDate (various entries)", async () => {
    mockDate("2020-07-15 12:30:00", 0);
    patchWithCleanup(localization, {
        dateFormat,
        timeFormat,
        dateTimeFormat: `${dateFormat} ${timeFormat}`,
    });

    /**
     * Type of testSet key: string
     * Type of testSet value: string | undefined
     */
    const testSet = new Map([
        ["10101010101010", undefined],
        ["1191111", "1191-04-21T00:00:00.000Z"], // day 111 of year 1191
        ["11911111", "1191-11-11T00:00:00.000Z"],
        ["3101", "2020-01-31T00:00:00.000Z"],
        ["310160", "2060-01-31T00:00:00.000Z"],
        ["311260", "2060-12-31T00:00:00.000Z"],

        ["310161", "1961-01-31T00:00:00.000Z"],
        ["310165", "1965-01-31T00:00:00.000Z"],
        ["310168", "1968-01-31T00:00:00.000Z"],
        ["311268", "1968-12-31T00:00:00.000Z"],

        ["310169", "1969-01-31T00:00:00.000Z"],
        ["310170", "1970-01-31T00:00:00.000Z"],
        ["310197", "1997-01-31T00:00:00.000Z"],
        ["310117", "2017-01-31T00:00:00.000Z"],
        ["31011985", "1985-01-31T00:00:00.000Z"],
        ["3101198508", undefined],
        ["310119850833", undefined],

        ["1137", undefined],
        ["1197", undefined],
        ["0131", undefined],
        ["0922", undefined],
        ["2020", undefined],

        ["199901", "1999-01-01T00:00:00.000Z"],
        ["30100210", "3010-02-10T00:00:00.000Z"],
        ["3010210", "3010-07-29T00:00:00.000Z"],

        ["970131", undefined],
        ["31.01", "2020-01-31T00:00:00.000Z"],
        ["31/01/1985 08", undefined],

        ["01121934", "1934-12-01T00:00:00.000Z"],
        ["011234", "2034-12-01T00:00:00.000Z"],
        ["011260", "2060-12-01T00:00:00.000Z"],
        ["2", "2020-07-02T00:00:00.000Z"],
        ["02", "2020-07-02T00:00:00.000Z"],
        ["20", "2020-07-20T00:00:00.000Z"],
        ["202", "2020-02-20T00:00:00.000Z"],
        ["2002", "2020-02-20T00:00:00.000Z"],
        ["0202", "2020-02-02T00:00:00.000Z"],
        ["02/02", "2020-02-02T00:00:00.000Z"],
        ["02/13", undefined],
        ["02/1313", undefined],
        ["09990101", undefined],
        ["19990101", "1999-01-01T00:00:00.000Z"],
        ["19990130", "1999-01-30T00:00:00.000Z"],
        ["19991230", "1999-12-30T00:00:00.000Z"],
        ["19993012", undefined],
        ["2016-200", "2016-07-18T00:00:00.000Z"],
        ["2016200", "2016-07-18T00:00:00.000Z"], // day 200 of year 2016
        ["2020-", undefined],
        ["2020-W2", undefined],
        ["2020W23", "2020-06-01T00:00:00.000Z"],
        ["2020-W02", "2020-01-06T00:00:00.000Z"],
        ["2020-W32", "2020-08-03T00:00:00.000Z"],
        ["2020-W32-3", "2020-08-05T00:00:00.000Z"],
        ["2016-W21-3", "2016-05-25T00:00:00.000Z"],
        ["2016W213", "2016-05-25T00:00:00.000Z"],
        ["2209", "2020-09-22T00:00:00.000Z"],
        ["22:09", "2020-09-22T00:00:00.000Z"],
        ["2012", "2020-12-20T00:00:00.000Z"],

        ["2016-01-03 09:24:15.123", "2016-01-03T00:00:00.000Z"],
        ["2016-01-03T09:24:15.123", "2016-01-03T00:00:00.000Z"],
        ["2016-01-03T09:24:15.123+06:00", "2016-01-03T00:00:00.000Z"],
        ["2016-01-03T09:24:15.123+16:00", "2016-01-02T00:00:00.000Z"],
        ["2016-01-03T09:24:15.123Z", "2016-01-03T00:00:00.000Z"],
        ["2016-W21-3T09:24:15.123", "2016-05-25T00:00:00.000Z"],
        ["2016-W21-3 09:24:15.123", undefined],

        ["2016-03-27T02:00:00.000+02:00", "2016-03-27T00:00:00.000Z"],
        ["2016-03-27T03:00:00.000+02:00", "2016-03-27T00:00:00.000Z"],
        ["2016-03-27T02:00:00.000", "2016-03-27T00:00:00.000Z"],
        ["2016-03-27T03:00:00.000", "2016-03-27T00:00:00.000Z"],
        ["2016-03-27T02:00:00.000Z", "2016-03-27T00:00:00.000Z"],
        ["2016-03-27T03:00:00.000Z", "2016-03-27T00:00:00.000Z"],

        ["09:22", undefined],
        ["2013", undefined],
        ["011261", "1961-12-01T00:00:00.000Z"],

        ["932-10-10", undefined], // year < 1000 are not supported
        ["1932-10-10", "1932-10-10T00:00:00.000Z"],
        ["2016-01-03 09:24:15.123+06:00", "2016-01-03T00:00:00.000Z"],
        ["2016-01-03 09:24:15.123+16:00", "2016-01-02T00:00:00.000Z"],
        ["2016-01-03 09:24:15.123Z", "2016-01-03T00:00:00.000Z"],
    ]);

    for (const [input, expected] of testSet.entries()) {
        if (!expected) {
            expect(() => parseDate(input).toISO()).toThrow(/is not a correct/);
        } else {
            expect(parseDate(input).toISO()).toBe(expected);
        }
    }
});

test("parseDateTime (various entries)", async () => {
    mockDate("2020-07-15 11:30:00", 0);
    patchWithCleanup(localization, {
        dateFormat,
        timeFormat,
        dateTimeFormat: `${dateFormat} ${timeFormat}`,
    });

    /**
     * Type of testSet key: string
     * Type of testSet value: string | undefined
     */
    const testSet = new Map([
        ["10101010101010", "1010-10-10T10:10:10.000Z"],
        ["1191111", "1191-04-21T00:00:00.000Z"], // day 111 of year 1191
        ["11911111", "1191-11-11T00:00:00.000Z"],
        ["3101", "2020-01-31T00:00:00.000Z"],
        ["310160", "2060-01-31T00:00:00.000Z"],
        ["311260", "2060-12-31T00:00:00.000Z"],
        ["310161", "1961-01-31T00:00:00.000Z"],
        ["310165", "1965-01-31T00:00:00.000Z"],
        ["310168", "1968-01-31T00:00:00.000Z"],
        ["311268", "1968-12-31T00:00:00.000Z"],
        ["310169", "1969-01-31T00:00:00.000Z"],
        ["310170", "1970-01-31T00:00:00.000Z"],
        ["310197", "1997-01-31T00:00:00.000Z"],
        ["310117", "2017-01-31T00:00:00.000Z"],
        ["31011985", "1985-01-31T00:00:00.000Z"],
        ["3101198508", "1985-01-31T08:00:00.000Z"],
        ["310119850833", "1985-01-31T08:33:00.000Z"],
        ["1137", undefined],
        ["1197", undefined],
        ["0131", undefined],
        ["0922", undefined],
        ["2020", undefined],
        ["199901", "1999-01-01T00:00:00.000Z"],
        ["30100210", "3010-02-10T00:00:00.000Z"],
        ["3010210", "3010-07-29T00:00:00.000Z"],
        ["970131", undefined],
        ["31.01", "2020-01-31T00:00:00.000Z"],
        ["31/01/1985 08", "1985-01-31T08:00:00.000Z"],

        ["01121934", "1934-12-01T00:00:00.000Z"],
        ["011234", "2034-12-01T00:00:00.000Z"],
        ["011260", "2060-12-01T00:00:00.000Z"],
        ["2", "2020-07-02T00:00:00.000Z"],
        ["02", "2020-07-02T00:00:00.000Z"],
        ["20", "2020-07-20T00:00:00.000Z"],
        ["202", "2020-02-20T00:00:00.000Z"],
        ["2002", "2020-02-20T00:00:00.000Z"],
        ["0202", "2020-02-02T00:00:00.000Z"],
        ["02/02", "2020-02-02T00:00:00.000Z"],
        ["02/13", undefined],
        ["02/1313", undefined],
        ["09990101", undefined],
        ["19990101", "1999-01-01T00:00:00.000Z"],
        ["19990130", "1999-01-30T00:00:00.000Z"],
        ["19991230", "1999-12-30T00:00:00.000Z"],
        ["19993012", undefined],
        ["2016-200", "2016-07-18T00:00:00.000Z"],
        ["2016200", "2016-07-18T00:00:00.000Z"], // day 200 of year 2016
        ["2020-", undefined],
        ["2020-W2", undefined],
        ["2020W23", "2020-06-01T00:00:00.000Z"],
        ["2020-W02", "2020-01-06T00:00:00.000Z"],
        ["2020-W32", "2020-08-03T00:00:00.000Z"],
        ["2020-W32-3", "2020-08-05T00:00:00.000Z"],
        ["2016-W21-3", "2016-05-25T00:00:00.000Z"],
        ["2016W213", "2016-05-25T00:00:00.000Z"],
        ["2209", "2020-09-22T00:00:00.000Z"],
        ["22:09", "2020-09-22T00:00:00.000Z"],
        ["2012", "2020-12-20T00:00:00.000Z"],

        ["2016-01-03 09:24:15.123", "2016-01-03T09:24:15.123Z"],
        ["2016-01-03T09:24:15.123", "2016-01-03T09:24:15.123Z"],
        ["2016-01-03T09:24:15.123+06:00", "2016-01-03T03:24:15.123Z"],
        ["2016-01-03T09:24:15.123+16:00", "2016-01-02T17:24:15.123Z"],
        ["2016-01-03T09:24:15.123Z", "2016-01-03T09:24:15.123Z"],
        ["2016-W21-3T09:24:15.123", "2016-05-25T09:24:15.123Z"],
        ["2016-W21-3 09:24:15.123", undefined],

        ["2016-03-27T02:00:00.000+02:00", "2016-03-27T00:00:00.000Z"],
        ["2016-03-27T03:00:00.000+02:00", "2016-03-27T01:00:00.000Z"],
        ["2016-03-27T02:00:00.000", "2016-03-27T02:00:00.000Z"],
        ["2016-03-27T03:00:00.000", "2016-03-27T03:00:00.000Z"],
        ["2016-03-27T02:00:00.000Z", "2016-03-27T02:00:00.000Z"],
        ["2016-03-27T03:00:00.000Z", "2016-03-27T03:00:00.000Z"],

        ["09:22", undefined],
        ["2013", undefined],
        ["011261", "1961-12-01T00:00:00.000Z"],

        ["932-10-10", undefined],
        ["1932-10-10", "1932-10-10T00:00:00.000Z"],
        ["2016-01-03 09:24:15.123+06:00", "2016-01-03T03:24:15.123Z"],
        ["2016-01-03 09:24:15.123+16:00", "2016-01-02T17:24:15.123Z"],
        ["2016-01-03 09:24:15.123Z", "2016-01-03T09:24:15.123Z"],
    ]);

    for (const [input, expected] of testSet.entries()) {
        if (!expected) {
            expect(() => parseDateTime(input).toISO()).toThrow(/is not a correct/);
        } else {
            expect(parseDateTime(input).toISO()).toBe(expected);
        }
    }
});

test("parseDateTime: arab locale, latin numbering system as input", async () => {
    defineParams({
        lang: "ar_001",
        lang_parameters: {
            date_format: "%d %b, %Y",
            time_format: "%H:%M:%S",
        },
    });
    await makeMockEnv();

    // Check it works with arab
    expect(parseDateTime("١٥ يوليو, ٢٠٢٠ ١٢:٣٠:٤٣").toISO().split(".")[0]).toBe(
        "2020-07-15T12:30:43"
    );

    // Check it also works with latin numbers
    expect(parseDateTime("15 07, 2020 12:30:43").toISO().split(".")[0]).toBe("2020-07-15T12:30:43");
    expect(parseDateTime("22/01/2023").toISO().split(".")[0]).toBe("2023-01-22T00:00:00");
    expect(parseDateTime("2023-01-22").toISO().split(".")[0]).toBe("2023-01-22T00:00:00");
});
