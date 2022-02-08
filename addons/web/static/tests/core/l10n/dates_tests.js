/** @odoo-module **/

import {
    formatDate,
    formatDateTime,
    parseDate,
    parseDateTime,
    strftimeToLuxonFormat,
} from "@web/core/l10n/dates";
import { localization } from "@web/core/l10n/localization";
import { patch, unpatch } from "@web/core/utils/patch";
import core from "web.core";
import field_utils from "web.field_utils";
import session from "web.session";
import test_utils from "web.test_utils";
import { registerCleanup } from "../../helpers/cleanup";
import { defaultLocalization } from "../../helpers/mock_services";
import { patchWithCleanup } from "../../helpers/utils";

const { DateTime, Settings } = luxon;

const legacy = {
    core,
    field_utils,
    session,
    test_utils,
};
const formats = {
    date: "%d.%m/%Y",
    time: "%H:%M:%S",
};
const dateFormat = strftimeToLuxonFormat(formats.date);
const timeFormat = strftimeToLuxonFormat(formats.time);

function runTestSet(assert, testSet, options) {
    for (const [input, expected] of testSet.entries()) {
        let res1;
        let res2;
        try {
            res1 = options.newFn(input);
        } catch (e) {}

        try {
            res2 = options.legacyFn(input);
        } catch (e) {}

        const expect =
            expected.length === 1
                ? {
                      new: expected[0],
                      legacy: expected[0],
                  }
                : {
                      new: expected[0],
                      legacy: expected[1],
                  };

        assert.deepEqual(res1, expect.new, `"${input}" is parsed as expected. [new]`);
        assert.deepEqual(res2, expect.legacy, `"${input}" is parsed as expected. [legacy]`);
    }
}

QUnit.module(
    "utils",
    {
        before() {
            moment.suppressDeprecationWarnings = true;
        },
        after() {
            moment.suppressDeprecationWarnings = false;
        },
    },
    () => {
        QUnit.module("dates");

        QUnit.test("formatDate", async (assert) => {
            patch(localization, "dateformat", { dateFormat: "MM/dd/yyyy" });

            let formatted = formatDate(DateTime.utc(2009, 5, 4, 12, 34, 23));
            let expected = "05/04/2009";
            assert.strictEqual(formatted, expected);

            formatted = formatDate(DateTime.utc(2009, 5, 4, 12, 34, 23), { timezone: false });
            assert.strictEqual(formatted, expected);

            formatted = formatDate(DateTime.utc(2009, 5, 4, 12, 34, 23), { timezone: true });
            expected = "05/04/2009";
            assert.strictEqual(formatted, expected);

            unpatch(localization, "dateformat");
        });

        QUnit.test("formatDate (with different timezone offset)", async (assert) => {
            patch(localization, "dateformat", { dateFormat: "MM/dd/yyyy" });

            let str = formatDate(DateTime.utc(2017, 1, 1, 10, 0, 0, 0));
            assert.strictEqual(str, "01/01/2017");
            str = formatDate(DateTime.utc(2017, 6, 1, 10, 0, 0, 0));
            assert.strictEqual(str, "06/01/2017");

            str = formatDate(DateTime.utc(2017, 1, 1, 10, 0, 0, 0), { timezone: false });
            assert.strictEqual(str, "01/01/2017");
            str = formatDate(DateTime.utc(2017, 6, 1, 10, 0, 0, 0), { timezone: false });
            assert.strictEqual(str, "06/01/2017");

            str = formatDate(DateTime.utc(2017, 1, 1, 10, 0, 0, 0), { timezone: true });
            assert.strictEqual(str, "01/01/2017");
            str = formatDate(DateTime.utc(2017, 6, 1, 10, 0, 0, 0), { timezone: true });
            assert.strictEqual(str, "06/01/2017");

            unpatch(localization, "dateformat");
        });

        QUnit.test("formatDateTime", async (assert) => {
            patch(localization, "datetimeformat", { dateTimeFormat: "MM/dd/yyyy HH:mm:ss" });

            let formatted = formatDateTime(DateTime.utc(2009, 5, 4, 12, 34, 23));
            let expected = "05/04/2009 12:34:23";
            assert.strictEqual(formatted, expected);

            formatted = formatDateTime(DateTime.utc(2009, 5, 4, 12, 34, 23), { timezone: false });
            assert.strictEqual(formatted, expected);

            formatted = formatDateTime(DateTime.utc(2009, 5, 4, 12, 34, 23), { timezone: true });
            expected = "05/04/2009 14:34:23";
            assert.strictEqual(formatted, expected);

            unpatch(localization, "datetimeformat");
        });

        QUnit.test("formatDateTime (with different timezone offset)", async (assert) => {
            patch(localization, "datetimeformat", { dateTimeFormat: "MM/dd/yyyy HH:mm:ss" });

            let str = formatDateTime(DateTime.utc(2017, 1, 1, 10, 0, 0, 0));
            assert.strictEqual(str, "01/01/2017 10:00:00");
            str = formatDateTime(DateTime.utc(2017, 6, 1, 10, 0, 0, 0));
            assert.strictEqual(str, "06/01/2017 10:00:00");

            str = formatDateTime(DateTime.utc(2017, 1, 1, 10, 0, 0, 0), { timezone: false });
            assert.strictEqual(str, "01/01/2017 10:00:00");
            str = formatDateTime(DateTime.utc(2017, 6, 1, 10, 0, 0, 0), { timezone: false });
            assert.strictEqual(str, "06/01/2017 10:00:00");

            str = formatDateTime(DateTime.utc(2017, 1, 1, 10, 0, 0, 0), { timezone: true });
            assert.strictEqual(str, "01/01/2017 11:00:00");
            str = formatDateTime(DateTime.utc(2017, 6, 1, 10, 0, 0, 0), { timezone: true });
            assert.strictEqual(str, "06/01/2017 12:00:00");

            unpatch(localization, "datetimeformat");
        });

        QUnit.test("parseDateTime", async (assert) => {
            patch(localization, "default loc", defaultLocalization);

            assert.throws(
                function () {
                    parseDateTime("13/01/2019 12:00:00");
                },
                /is not a correct/,
                "Wrongly formated dates should be invalid"
            );
            assert.throws(
                function () {
                    parseDateTime("01/01/0999 12:00:00");
                },
                /is not a correct/,
                "Dates before 1000 should be invalid"
            );
            assert.throws(
                function () {
                    parseDateTime("01/01/10000 12:00:00");
                },
                /is not a correct/,
                "Dates after 9999 should be invalid"
            );
            assert.throws(function () {
                parseDateTime("invalid value");
            }, /is not a correct/);

            let expected = "2019-01-13T10:05:45.000Z";
            let dateStr = "01/13/2019 10:05:45";
            assert.equal(parseDateTime(dateStr).toISO(), expected, "Date with leading 0");
            dateStr = "1/13/2019 10:5:45";
            assert.equal(parseDateTime(dateStr).toISO(), expected, "Date without leading 0");

            unpatch(localization, "default loc");
        });

        QUnit.test("parseDateTime (norwegian locale)", async (assert) => {
            const dateFormat = strftimeToLuxonFormat("%d. %b %Y");
            const timeFormat = strftimeToLuxonFormat("%H:%M:%S");
            patch(localization, "weird loc", {
                dateFormat,
                timeFormat,
                dateTimeFormat: `${dateFormat} ${timeFormat}`,
            });

            // Before WOWL we were using MomentJS.
            // Now it has been replaced by luxon.js, we cannot declare customized locales.
            // In legacy web, parseDateTime tests were originally defining custom locales
            // for english and norwegian.
            // Here, we simply use the vanilla Intl support to switch locale.
            const originalLocale = Settings.defaultLocale;
            Settings.defaultLocale = "no"; // Norwegian

            const dateStr = "16. des 2019 10:05:45";
            const expected = "2019-12-16T10:05:45.000Z";
            assert.equal(
                parseDateTime(dateStr).toISO(),
                expected,
                "Day/month inverted + month i18n"
            );

            Settings.defaultLocale = originalLocale;
            unpatch(localization, "weird loc");
        });

        QUnit.test("parseDate without separator", async (assert) => {
            const dateFormat = strftimeToLuxonFormat("%d.%m/%Y");
            const timeFormat = strftimeToLuxonFormat("%H:%M:%S");
            patch(localization, "patch loc", {
                dateFormat,
                timeFormat,
                dateTimeFormat: `${dateFormat} ${timeFormat}`,
            });

            const testDateFormat = "dd.MM/yyyy";

            assert.throws(
                function () {
                    parseDate("1137");
                },
                /is not a correct/,
                "Wrongly formated dates should be invalid"
            );
            assert.throws(
                function () {
                    parseDate("1197");
                },
                /is not a correct/,
                "Wrongly formated dates should be invalid"
            );
            assert.throws(
                function () {
                    parseDate("0131");
                },
                /is not a correct/,
                "Wrongly formated dates should be invalid"
            );
            assert.throws(
                function () {
                    parseDate("970131");
                },
                /is not a correct/,
                "Wrongly formated dates should be invalid"
            );
            assert.equal(
                parseDate("2001").toFormat(testDateFormat),
                "20.01/" + DateTime.utc().year
            );
            assert.equal(
                parseDate("3101").toFormat(testDateFormat),
                "31.01/" + DateTime.utc().year
            );
            assert.equal(
                parseDate("31.01").toFormat(testDateFormat),
                "31.01/" + DateTime.utc().year
            );
            assert.equal(parseDate("310197").toFormat(testDateFormat), "31.01/1997");
            assert.equal(parseDate("310117").toFormat(testDateFormat), "31.01/2017");
            assert.equal(parseDate("31011985").toFormat(testDateFormat), "31.01/1985");
            unpatch(localization, "patch loc");
        });

        QUnit.test("parseDateTime without separator", async (assert) => {
            const dateFormat = strftimeToLuxonFormat("%d.%m/%Y");
            const timeFormat = strftimeToLuxonFormat("%H:%M:%S");
            patch(localization, "patch loc", {
                dateFormat,
                timeFormat,
                dateTimeFormat: `${dateFormat} ${timeFormat}`,
            });

            const dateTimeFormat = "dd.MM/yyyy HH:mm/ss";
            assert.equal(
                parseDateTime("3101198508").toFormat(dateTimeFormat),
                "31.01/1985 08:00/00"
            );
            assert.equal(
                parseDateTime("310119850833").toFormat(dateTimeFormat),
                "31.01/1985 08:33/00"
            );
            assert.equal(
                parseDateTime("31/01/1985 08").toFormat(dateTimeFormat),
                "31.01/1985 08:00/00"
            );
            unpatch(localization, "patch loc");
        });

        QUnit.test("parse smart date input", async (assert) => {
            const format = "dd MM yyyy";
            assert.strictEqual(
                parseDate("+1d").toFormat(format),
                DateTime.utc().plus({ days: 1 }).toFormat(format)
            );
            assert.strictEqual(
                parseDateTime("+2w").toFormat(format),
                DateTime.utc().plus({ weeks: 2 }).toFormat(format)
            );
            assert.strictEqual(
                parseDate("+3m").toFormat(format),
                DateTime.utc().plus({ months: 3 }).toFormat(format)
            );
            assert.strictEqual(
                parseDateTime("+4y").toFormat(format),
                DateTime.utc().plus({ years: 4 }).toFormat(format)
            );
            assert.strictEqual(
                parseDate("+5").toFormat(format),
                DateTime.utc().plus({ days: 5 }).toFormat(format)
            );
            assert.strictEqual(
                parseDateTime("-5").toFormat(format),
                DateTime.utc().minus({ days: 5 }).toFormat(format)
            );
            assert.strictEqual(
                parseDate("-4y").toFormat(format),
                DateTime.utc().minus({ years: 4 }).toFormat(format)
            );
            assert.strictEqual(
                parseDateTime("-3m").toFormat(format),
                DateTime.utc().minus({ months: 3 }).toFormat(format)
            );
            assert.strictEqual(
                parseDate("-2w").toFormat(format),
                DateTime.utc().minus({ weeks: 2 }).toFormat(format)
            );
            assert.strictEqual(
                parseDateTime("-1d").toFormat(format),
                DateTime.utc().minus({ days: 1 }).toFormat(format)
            );
        });

        QUnit.test("parseDateTime SQL Format", async (assert) => {
            patch(localization, "default loc", defaultLocalization);

            let dateStr = "2017-05-15 09:12:34";
            let expected = "2017-05-15T09:12:34.000Z";
            assert.equal(parseDateTime(dateStr).toISO(), expected, "Date with SQL format");

            dateStr = "2017-05-08 09:12:34";
            expected = "2017-05-08T09:12:34.000Z";
            assert.equal(
                parseDateTime(dateStr).toISO(),
                expected,
                "Date SQL format, check date is not confused with month"
            );

            unpatch(localization, "default loc");
        });

        QUnit.module("dates utils compatibility with legacy", {
            beforeEach() {
                patchWithCleanup(localization, {
                    dateFormat,
                    timeFormat,
                    dateTimeFormat: `${dateFormat} ${timeFormat}`,
                });

                patchWithCleanup(legacy.core._t.database.parameters, {
                    date_format: formats.date,
                    time_format: formats.time,
                });

                // Patch legacy session
                const initialSession = Object.assign({}, legacy.session);
                const sessionPatch = {
                    getTZOffset(date) {
                        const offset = DateTime.local().zone.offset(date.valueOf());
                        return offset;
                    },
                };
                Object.assign(legacy.session, sessionPatch);
                registerCleanup(() => {
                    for (let key in sessionPatch) {
                        delete legacy.session[key];
                    }
                    Object.assign(legacy.session, initialSession);
                });

                // Patch legacy date (will also work for new dates utils): 15th July 2020 12h30
                const unpatchDate = legacy.test_utils.mock.patchDate(2020, 6, 15, 12, 30, 0);
                registerCleanup(() => {
                    if (unpatchDate) {
                        unpatchDate();
                    }
                });
            },
        });

        QUnit.test("parseDate", async (assert) => {
            /**
             * Type of testSet key: string
             * Type of testSet value: [newExpected: string, legacyExpected: string]
             */
            const testSet = new Map([
                ["10101010101010", ["1010-10-10T00:00:00.000Z"]],
                ["1191111", ["1191-04-21T00:00:00.000Z"]], // day 111 of year 1191
                ["11911111", ["1191-11-11T00:00:00.000Z"]],
                ["3101", ["2020-01-31T00:00:00.000Z"]],
                ["310160", ["2060-01-31T00:00:00.000Z"]],
                ["311260", ["2060-12-31T00:00:00.000Z"]],

                ["310161", ["1961-01-31T00:00:00.000Z", "2061-01-31T00:00:00.000Z"]], // moment vs luxon 19xx/20xx thresholds
                ["310165", ["1965-01-31T00:00:00.000Z", "2065-01-31T00:00:00.000Z"]], // moment vs luxon 19xx/20xx thresholds
                ["310168", ["1968-01-31T00:00:00.000Z", "2068-01-31T00:00:00.000Z"]], // moment vs luxon 19xx/20xx thresholds
                ["311268", ["1968-12-31T00:00:00.000Z", "2068-12-31T00:00:00.000Z"]], // moment vs luxon 19xx/20xx thresholds

                ["310169", ["1969-01-31T00:00:00.000Z"]],
                ["310170", ["1970-01-31T00:00:00.000Z"]],
                ["310197", ["1997-01-31T00:00:00.000Z"]],
                ["310117", ["2017-01-31T00:00:00.000Z"]],
                ["31011985", ["1985-01-31T00:00:00.000Z"]],
                ["3101198508", ["1985-01-31T00:00:00.000Z"]],
                ["310119850833", ["1985-01-31T00:00:00.000Z"]],

                ["1137", [undefined]],
                ["1197", [undefined]],
                ["0131", [undefined]],
                ["0922", [undefined]],
                ["2020", [undefined]],

                ["199901", ["1999-01-01T00:00:00.000Z", undefined]],
                ["30100210", ["3010-02-10T00:00:00.000Z", undefined]],
                ["3010210", ["3010-07-29T00:00:00.000Z", undefined]],

                ["970131", [undefined]],
                ["31.01", ["2020-01-31T00:00:00.000Z"]],
                ["31/01/1985 08", ["1985-01-31T00:00:00.000Z"]],

                ["01121934", ["1934-12-01T00:00:00.000Z"]],
                ["011234", ["2034-12-01T00:00:00.000Z"]],
                ["011260", ["2060-12-01T00:00:00.000Z"]],
                ["2", ["2020-07-02T00:00:00.000Z"]],
                ["02", ["2020-07-02T00:00:00.000Z"]],
                ["20", ["2020-07-20T00:00:00.000Z"]],
                ["202", ["2020-02-20T00:00:00.000Z"]],
                ["2002", ["2020-02-20T00:00:00.000Z"]],
                ["0202", ["2020-02-02T00:00:00.000Z"]],
                ["02/02", ["2020-02-02T00:00:00.000Z"]],
                ["02/13", [undefined]],
                ["02/1313", [undefined]],
                ["09990101", [undefined]],
                ["19990101", ["1999-01-01T00:00:00.000Z"]],
                ["19990130", ["1999-01-30T00:00:00.000Z"]],
                ["19991230", ["1999-12-30T00:00:00.000Z"]],
                ["19993012", [undefined]],
                ["2016-200", ["2016-07-18T00:00:00.000Z"]],
                ["2016200", ["2016-07-18T00:00:00.000Z"]], // day 200 of year 2016
                ["2020-", [undefined]],
                ["2020-W2", [undefined]],
                ["2020W23", ["2020-06-01T00:00:00.000Z"]],
                ["2020-W02", ["2020-01-06T00:00:00.000Z"]],
                ["2020-W32", ["2020-08-03T00:00:00.000Z"]],
                ["2020-W32-3", ["2020-08-05T00:00:00.000Z"]],
                ["2016-W21-3", ["2016-05-25T00:00:00.000Z"]],
                ["2016W213", ["2016-05-25T00:00:00.000Z"]],
                ["2209", ["2020-09-22T00:00:00.000Z"]],
                ["22:09", ["2020-09-22T00:00:00.000Z"]],
                ["2012", ["2020-12-20T00:00:00.000Z"]],

                [
                    "2016-01-03 09:24:15.123",
                    ["2016-01-03T00:00:00.000Z", "2016-01-03T09:24:15.123Z"],
                ],
                [
                    "2016-01-03T09:24:15.123",
                    ["2016-01-03T00:00:00.000Z", "2016-01-03T09:24:15.123Z"],
                ],
                [
                    "2016-01-03T09:24:15.123+06:00",
                    ["2016-01-03T00:00:00.000Z", "2016-01-03T03:24:15.123Z"],
                ],
                [
                    "2016-01-03T09:24:15.123+16:00",
                    ["2016-01-02T00:00:00.000Z", "2016-01-02T17:24:15.123Z"],
                ],
                [
                    "2016-01-03T09:24:15.123Z",
                    ["2016-01-03T00:00:00.000Z", "2016-01-03T09:24:15.123Z"],
                ],
                [
                    "2016-W21-3T09:24:15.123",
                    ["2016-05-25T00:00:00.000Z", "2016-05-25T09:24:15.123Z"],
                ],
                ["2016-W21-3 09:24:15.123", [undefined, "2016-05-25T09:24:15.123Z"]],

                ["2016-03-27T02:00:00.000+02:00", ["2016-03-27T00:00:00.000Z"]],
                [
                    "2016-03-27T03:00:00.000+02:00",
                    ["2016-03-27T00:00:00.000Z", "2016-03-27T01:00:00.000Z"],
                ],
                [
                    "2016-03-27T02:00:00.000",
                    ["2016-03-27T00:00:00.000Z", "2016-03-27T02:00:00.000Z"],
                ],
                [
                    "2016-03-27T03:00:00.000",
                    ["2016-03-27T00:00:00.000Z", "2016-03-27T03:00:00.000Z"],
                ],
                [
                    "2016-03-27T02:00:00.000Z",
                    ["2016-03-27T00:00:00.000Z", "2016-03-27T02:00:00.000Z"],
                ],
                [
                    "2016-03-27T03:00:00.000Z",
                    ["2016-03-27T00:00:00.000Z", "2016-03-27T03:00:00.000Z"],
                ],

                ["09:22", [undefined]],
                ["2013", [undefined]],
                ["011261", ["1961-12-01T00:00:00.000Z", "2061-12-01T00:00:00.000Z"]],
            ]);

            runTestSet(assert, testSet, {
                newFn: (input) => parseDate(input).toISO(),
                legacyFn: (input) => legacy.field_utils.parse.date(input).toISOString(),
            });
        });

        QUnit.test("parseDate (with legacy options.isUTC = true)", async (assert) => {
            /**
             * Type of testSet key: string
             * Type of testSet value: [newExpected: string, legacyExpected: string]
             */
            const testSet = new Map([
                ["932-10-10", [undefined]], // year < 1000 are not supported
                ["1932-10-10", ["1932-10-10T00:00:00.000Z"]],
                ["09990101", [undefined]], // year < 1000 are not supported
                ["19993012", [undefined]], // there is no 30th month
                ["19990101", ["1999-01-01T00:00:00.000Z", undefined]],
                ["19990130", ["1999-01-30T00:00:00.000Z", undefined]],
                ["19991230", ["1999-12-30T00:00:00.000Z", undefined]],
                [
                    "2016-01-03 09:24:15.123",
                    ["2016-01-03T00:00:00.000Z", "2016-01-03T09:24:15.123Z"],
                ], // Outputting the time was weird in legacy anyway
                [
                    "2016-01-03T09:24:15.123",
                    ["2016-01-03T00:00:00.000Z", "2016-01-03T09:24:15.123Z"],
                ], // Outputting the time was weird in legacy anyway
                [
                    "2016-01-03 09:24:15.123+06:00",
                    ["2016-01-03T00:00:00.000Z", "2016-01-03T03:24:15.123Z"],
                ], // Outputting the time was weird in legacy anyway
                [
                    "2016-01-03T09:24:15.123+06:00",
                    ["2016-01-03T00:00:00.000Z", "2016-01-03T03:24:15.123Z"],
                ], // Outputting the time was weird in legacy anyway
                [
                    "2016-01-03 09:24:15.123+16:00",
                    ["2016-01-02T00:00:00.000Z", "2016-01-02T17:24:15.123Z"],
                ], // Outputting the time was weird in legacy anyway
                [
                    "2016-01-03T09:24:15.123+16:00",
                    ["2016-01-02T00:00:00.000Z", "2016-01-02T17:24:15.123Z"],
                ], // Outputting the time was weird in legacy anyway
                [
                    "2016-01-03 09:24:15.123Z",
                    ["2016-01-03T00:00:00.000Z", "2016-01-03T09:24:15.123Z"],
                ], // Outputting the time was weird in legacy anyway
                [
                    "2016-01-03T09:24:15.123Z",
                    ["2016-01-03T00:00:00.000Z", "2016-01-03T09:24:15.123Z"],
                ], // Outputting the time was weird in legacy anyway
            ]);

            runTestSet(assert, testSet, {
                newFn: (input) => parseDate(input, { format: "YYYY-MM-DD" }).toISO(),
                legacyFn: (input) =>
                    legacy.field_utils.parse.date(input, null, { isUTC: true }).toISOString(),
            });
        });

        QUnit.test("parseDateTime", async (assert) => {
            /**
             * Type of testSet key: string
             * Type of testSet value: [newExpected: string, legacyExpected: string]
             */
            const testSet = new Map([
                ["10101010101010", ["1010-10-10T10:10:10.000Z"]],
                ["1191111", ["1191-04-21T00:00:00.000Z"]], // day 111 of year 1191
                ["11911111", ["1191-11-11T00:00:00.000Z"]],
                ["3101", ["2020-01-31T00:00:00.000Z"]],
                ["310160", ["2060-01-31T00:00:00.000Z"]],
                ["311260", ["2060-12-31T00:00:00.000Z"]],
                ["310161", ["1961-01-31T00:00:00.000Z", "2061-01-31T00:00:00.000Z"]],
                ["310165", ["1965-01-31T00:00:00.000Z", "2065-01-31T00:00:00.000Z"]],
                ["310168", ["1968-01-31T00:00:00.000Z", "2068-01-31T00:00:00.000Z"]],
                ["311268", ["1968-12-31T00:00:00.000Z", "2068-12-31T00:00:00.000Z"]],
                ["310169", ["1969-01-31T00:00:00.000Z"]],
                ["310170", ["1970-01-31T00:00:00.000Z"]],
                ["310197", ["1997-01-31T00:00:00.000Z"]],
                ["310117", ["2017-01-31T00:00:00.000Z"]],
                ["31011985", ["1985-01-31T00:00:00.000Z"]],
                ["3101198508", ["1985-01-31T08:00:00.000Z"]],
                ["310119850833", ["1985-01-31T08:33:00.000Z"]],
                ["1137", [undefined]],
                ["1197", [undefined]],
                ["0131", [undefined]],
                ["0922", [undefined]],
                ["2020", [undefined]],
                ["199901", ["1999-01-01T00:00:00.000Z", undefined]],
                ["30100210", ["3010-02-10T00:00:00.000Z"]],
                ["3010210", ["3010-07-29T00:00:00.000Z"]],
                ["970131", [undefined]],
                ["31.01", ["2020-01-31T00:00:00.000Z"]],
                ["31/01/1985 08", ["1985-01-31T08:00:00.000Z"]],

                ["01121934", ["1934-12-01T00:00:00.000Z"]],
                ["011234", ["2034-12-01T00:00:00.000Z"]],
                ["011260", ["2060-12-01T00:00:00.000Z"]],
                ["2", ["2020-07-02T00:00:00.000Z"]],
                ["02", ["2020-07-02T00:00:00.000Z"]],
                ["20", ["2020-07-20T00:00:00.000Z"]],
                ["202", ["2020-02-20T00:00:00.000Z"]],
                ["2002", ["2020-02-20T00:00:00.000Z"]],
                ["0202", ["2020-02-02T00:00:00.000Z"]],
                ["02/02", ["2020-02-02T00:00:00.000Z"]],
                ["02/13", [undefined]],
                ["02/1313", [undefined]],
                ["09990101", [undefined]],
                ["19990101", ["1999-01-01T00:00:00.000Z"]],
                ["19990130", ["1999-01-30T00:00:00.000Z"]],
                ["19991230", ["1999-12-30T00:00:00.000Z"]],
                ["19993012", [undefined]],
                ["2016-200", ["2016-07-18T00:00:00.000Z"]],
                ["2016200", ["2016-07-18T00:00:00.000Z"]], // day 200 of year 2016
                ["2020-", [undefined]],
                ["2020-W2", [undefined]],
                ["2020W23", ["2020-06-01T00:00:00.000Z"]],
                ["2020-W02", ["2020-01-06T00:00:00.000Z"]],
                ["2020-W32", ["2020-08-03T00:00:00.000Z"]],
                ["2020-W32-3", ["2020-08-05T00:00:00.000Z"]],
                ["2016-W21-3", ["2016-05-25T00:00:00.000Z"]],
                ["2016W213", ["2016-05-25T00:00:00.000Z"]],
                ["2209", ["2020-09-22T00:00:00.000Z"]],
                ["22:09", ["2020-09-22T00:00:00.000Z"]],
                ["2012", ["2020-12-20T00:00:00.000Z"]],

                ["2016-01-03 09:24:15.123", ["2016-01-03T09:24:15.123Z"]],
                ["2016-01-03T09:24:15.123", ["2016-01-03T09:24:15.123Z"]],
                ["2016-01-03T09:24:15.123+06:00", ["2016-01-03T03:24:15.123Z"]],
                ["2016-01-03T09:24:15.123+16:00", ["2016-01-02T17:24:15.123Z"]],
                ["2016-01-03T09:24:15.123Z", ["2016-01-03T09:24:15.123Z"]],
                ["2016-W21-3T09:24:15.123", ["2016-05-25T09:24:15.123Z"]],
                ["2016-W21-3 09:24:15.123", [undefined, "2016-05-25T09:24:15.123Z"]],

                ["2016-03-27T02:00:00.000+02:00", ["2016-03-27T00:00:00.000Z"]],
                ["2016-03-27T03:00:00.000+02:00", ["2016-03-27T01:00:00.000Z"]],
                ["2016-03-27T02:00:00.000", ["2016-03-27T02:00:00.000Z"]],
                ["2016-03-27T03:00:00.000", ["2016-03-27T03:00:00.000Z"]],
                ["2016-03-27T02:00:00.000Z", ["2016-03-27T02:00:00.000Z"]],
                ["2016-03-27T03:00:00.000Z", ["2016-03-27T03:00:00.000Z"]],

                ["09:22", [undefined]],
                ["2013", [undefined]],
                ["011261", ["1961-12-01T00:00:00.000Z", "2061-12-01T00:00:00.000Z"]],
            ]);

            runTestSet(assert, testSet, {
                newFn: (input) => parseDateTime(input).toISO(),
                legacyFn: (input) => legacy.field_utils.parse.datetime(input).toISOString(),
            });
        });

        QUnit.test("parseDateTime (with legacy options.isUTC = true)", async (assert) => {
            /**
             * Type of testSet key: string
             * Type of testSet value: [newExpected: string, legacyExpected: string]
             */
            const testSet = new Map([
                ["932-10-10", [undefined, "2000-10-10T00:00:00.000Z"]], // weird behaviour in legacy
                ["1932-10-10", ["1932-10-10T00:00:00.000Z", "2000-10-10T00:00:00.000Z"]], // weird behaviour in legacy
                ["09990101", [undefined, "2000-01-01T00:00:00.000Z"]], // weird behaviour in legacy
                ["19993012", [undefined, "2000-01-01T00:00:00.000Z"]], // weird behaviour in legacy

                ["19990101", ["1999-01-01T00:00:00.000Z", "2000-01-01T00:00:00.000Z"]], // weird behaviour in legacy
                ["19990130", ["1999-01-30T00:00:00.000Z", "2000-01-01T00:00:00.000Z"]], // weird behaviour in legacy
                ["19991230", ["1999-12-30T00:00:00.000Z", "2000-01-01T00:00:00.000Z"]], // weird behaviour in legacy
                ["2016-01-03 09:24:15.123", ["2016-01-03T09:24:15.123Z"]],
                ["2016-01-03T09:24:15.123", ["2016-01-03T09:24:15.123Z"]],
                ["2016-01-03 09:24:15.123+06:00", ["2016-01-03T03:24:15.123Z", undefined]],
                ["2016-01-03T09:24:15.123+06:00", ["2016-01-03T03:24:15.123Z", undefined]],
                ["2016-01-03 09:24:15.123+16:00", ["2016-01-02T17:24:15.123Z", undefined]],
                ["2016-01-03T09:24:15.123+16:00", ["2016-01-02T17:24:15.123Z", undefined]],
                ["2016-01-03 09:24:15.123Z", ["2016-01-03T09:24:15.123Z", undefined]], // weird behaviour in legacy
                ["2016-01-03T09:24:15.123Z", ["2016-01-03T09:24:15.123Z", undefined]], // weird behaviour in legacy
            ]);

            runTestSet(assert, testSet, {
                newFn: (input) => parseDateTime(input, { format: "YYYY-MM-DD HH:mm:ss" }).toISO(),
                legacyFn: (input) =>
                    legacy.field_utils.parse.datetime(input, null, { isUTC: true }).toISOString(),
            });
        });

        QUnit.test("parseDateTime (with options.timezone = true)", async (assert) => {
            /**
             * Type of testSet key: string
             * Type of testSet value: [newExpected: string, legacyExpected: string]
             */
            const testSet = new Map([
                ["10101010101010", ["1010-10-10T09:52:40.000Z"]],
                ["1191111", ["1191-04-20T23:42:30.000Z"]], // day 111 of year 1191
                ["11911111", ["1191-11-10T23:42:30.000Z"]],
                ["3101", ["2020-01-30T23:00:00.000Z"]],
                ["310160", ["2060-01-30T23:00:00.000Z"]],
                ["311260", ["2060-12-30T23:00:00.000Z"]],
                ["310161", ["1961-01-30T23:00:00.000Z", "2061-01-30T23:00:00.000Z"]],
                ["310165", ["1965-01-30T23:00:00.000Z", "2065-01-30T23:00:00.000Z"]],
                ["310168", ["1968-01-30T23:00:00.000Z", "2068-01-30T23:00:00.000Z"]],
                ["311268", ["1968-12-30T23:00:00.000Z", "2068-12-30T23:00:00.000Z"]],
                ["310169", ["1969-01-30T23:00:00.000Z"]],
                ["310170", ["1970-01-30T23:00:00.000Z"]],
                ["310197", ["1997-01-30T23:00:00.000Z"]],
                ["310117", ["2017-01-30T23:00:00.000Z"]],
                ["31011985", ["1985-01-30T23:00:00.000Z"]],
                ["3101198508", ["1985-01-31T07:00:00.000Z"]],
                ["310119850833", ["1985-01-31T07:33:00.000Z"]],
                ["1137", [undefined]],
                ["1197", [undefined]],
                ["0131", [undefined]],
                ["0922", [undefined]],
                ["2020", [undefined]],
                ["199901", ["1998-12-31T23:00:00.000Z", undefined]],
                ["30100210", ["3010-02-09T23:00:00.000Z"]],
                ["3010210", ["3010-07-28T22:00:00.000Z"]],
                ["970131", [undefined]],
                ["31.01", ["2020-01-30T23:00:00.000Z"]],
                ["31/01/1985 08", ["1985-01-31T07:00:00.000Z"]],

                ["01121934", ["1934-12-01T00:00:00.000Z"]],
                ["011234", ["2034-11-30T23:00:00.000Z"]],
                ["011260", ["2060-11-30T23:00:00.000Z"]],
                ["2", ["2020-07-01T22:00:00.000Z"]],
                ["02", ["2020-07-01T22:00:00.000Z"]],
                ["20", ["2020-07-19T22:00:00.000Z"]],
                ["202", ["2020-02-19T23:00:00.000Z"]],
                ["2002", ["2020-02-19T23:00:00.000Z"]],
                ["0202", ["2020-02-01T23:00:00.000Z"]],
                ["02/02", ["2020-02-01T23:00:00.000Z"]],
                ["02/13", [undefined]],
                ["02/1313", [undefined]],
                ["09990101", [undefined]],
                ["19990101", ["1998-12-31T23:00:00.000Z"]],
                ["19990130", ["1999-01-29T23:00:00.000Z"]],
                ["19991230", ["1999-12-29T23:00:00.000Z"]],
                ["19993012", [undefined]],
                ["2016-200", ["2016-07-17T22:00:00.000Z"]],
                ["2016200", ["2016-07-17T22:00:00.000Z"]], // day 200 of year 2016
                ["2020-", [undefined]],
                ["2020-W2", [undefined]],
                ["2020W23", ["2020-05-31T22:00:00.000Z"]],
                ["2020-W02", ["2020-01-05T23:00:00.000Z"]],
                ["2020-W32", ["2020-08-02T22:00:00.000Z"]],
                ["2020-W32-3", ["2020-08-04T22:00:00.000Z"]],
                ["2016-W21-3", ["2016-05-24T22:00:00.000Z"]],
                ["2016W213", ["2016-05-24T22:00:00.000Z"]],
                ["2209", ["2020-09-21T22:00:00.000Z"]],
                ["22:09", ["2020-09-21T22:00:00.000Z"]], // FIXME ? Is this weird ?
                ["2012", ["2020-12-19T23:00:00.000Z"]],

                ["2016-01-03 09:24:15.123", ["2016-01-03T08:24:15.123Z"]],
                ["2016-01-03T09:24:15.123", ["2016-01-03T08:24:15.123Z"]],
                [
                    "2016-01-03T09:24:15.123+06:00",
                    ["2016-01-03T03:24:15.123Z", "2016-01-03T02:24:15.123Z"],
                ],
                [
                    "2016-01-03T09:24:15.123+16:00",
                    ["2016-01-02T17:24:15.123Z", "2016-01-02T16:24:15.123Z"],
                ],
                [
                    "2016-01-03T09:24:15.123Z",
                    ["2016-01-03T09:24:15.123Z", "2016-01-03T08:24:15.123Z"],
                ],
                ["2016-W21-3T09:24:15.123", ["2016-05-25T07:24:15.123Z"]],
                ["2016-W21-3 09:24:15.123", [undefined, "2016-05-25T07:24:15.123Z"]],

                [
                    "2016-03-27T02:00:00.000+02:00",
                    ["2016-03-27T00:00:00.000Z", "2016-03-26T23:00:00.000Z"],
                ],
                [
                    "2016-03-27T03:00:00.000+02:00",
                    ["2016-03-27T01:00:00.000Z", "2016-03-26T23:00:00.000Z"],
                ],
                [
                    "2016-03-27T02:00:00.000",
                    ["2016-03-27T01:00:00.000Z", "2016-03-27T00:00:00.000Z"],
                ],
                ["2016-03-27T03:00:00.000", ["2016-03-27T01:00:00.000Z"]],
                [
                    "2016-03-27T02:00:00.000Z",
                    ["2016-03-27T02:00:00.000Z", "2016-03-27T00:00:00.000Z"],
                ],
                [
                    "2016-03-27T03:00:00.000Z",
                    ["2016-03-27T03:00:00.000Z", "2016-03-27T01:00:00.000Z"],
                ],

                ["09:22", [undefined]],
                ["2013", [undefined]],
                ["011261", ["1961-11-30T23:00:00.000Z", "2061-11-30T23:00:00.000Z"]],
            ]);

            runTestSet(assert, testSet, {
                newFn: (input) => parseDateTime(input, { timezone: true }).toUTC().toISO(),
                legacyFn: (input) =>
                    legacy.field_utils.parse
                        .datetime(input, null, { timezone: true })
                        .toISOString(),
            });
        });
    }
);
