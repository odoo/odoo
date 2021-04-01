/** @odoo-module **/

import { strftimeToLuxonFormat } from "../../src/localization/localization_service";
import { localization } from "../../src/localization/localization_settings";
import { parseDateTime, formatDateTime, parseDate } from "../../src/utils/dates";
import { patch, unpatch } from "../../src/utils/patch";
import { defaultLocalization } from "../helpers/mocks";

const { DateTime, Settings } = luxon;

QUnit.module("utils", () => {
  QUnit.module("dates");

  QUnit.test("formatDateTime", async (assert) => {
    patch(localization, "datetimeformat", { dateTimeFormat: "MM/dd/yyyy HH:mm:ss" });
    const isoDateStr = "2009-05-04T12:34:23";
    const date = parseDateTime(isoDateStr);
    const str = formatDateTime(date, { timezone: false });
    assert.strictEqual(str, date.toFormat("MM/dd/yyyy HH:mm:ss"));
    unpatch(localization, "datetimeformat");
  });

  QUnit.test("formatDateTime (with different timezone offset)", async (assert) => {
    // BOI: with legacy web, date format was mocked but IMHO this is not needed here.
    patch(localization, "datetimeformat", { dateTimeFormat: "MM/dd/yyyy HH:mm:ss" });

    let str = formatDateTime(DateTime.utc(2017, 1, 1, 10, 0, 0, 0));
    assert.strictEqual(str, "01/01/2017 11:00:00");
    str = formatDateTime(DateTime.utc(2017, 6, 1, 10, 0, 0, 0));
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
        parseDateTime("01/01/10000 12:00:00");
      },
      /is not a correct/,
      "Dates after 9999 should be invalid"
    );
    let dateStr = "01/13/2019 10:05:45";
    let date1 = parseDateTime(dateStr);
    let date2 = DateTime.fromFormat(dateStr, "MM/dd/yyyy HH:mm:ss");
    assert.equal(date1.toISO(), date2.toISO(), "Date with leading 0");
    dateStr = "1/13/2019 10:5:45";
    date1 = parseDateTime(dateStr);
    date2 = DateTime.fromFormat(dateStr, "M/d/yyyy H:m:s");
    assert.equal(date1.toISO(), date2.toISO(), "Date without leading 0");
    dateStr = "01/01/0001 10:15:45";
    date1 = parseDateTime(dateStr);
    date2 = DateTime.fromFormat(dateStr, "MM/dd/yyyy HH:mm:ss");
    assert.equal(date1.toISO(), date2.toISO(), "can parse dates of year 1");
    dateStr = "1/1/1 10:15:45";
    date1 = parseDateTime(dateStr);
    date2 = DateTime.fromFormat(dateStr, "M/d/y H:m:s");
    assert.equal(date1.toISO(), date2.toISO(), "can parse dates of year 1");

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
    const date1 = parseDateTime(dateStr);
    const date2 = DateTime.fromFormat(dateStr, "d. MMM y H:m:s");
    assert.equal(date1.toISO(), date2.toISO(), "Day/month inverted + month i18n");
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

    // ---
    // In legacy web, the version of Moment is unable to parse the following cases.
    // Now that we use Luxon, these cases return valid DateTime objects,
    // as any recent version of Moment will also do.
    // assert.throws(
    //   function () {
    //     l10n.parseDate("1197");
    //   },
    //   /is not a correct/,
    //   "Wrongly formated dates should be invalid"
    // );
    // assert.throws(
    //   function () {
    //     l10n.parseDate("0131");
    //   },
    //   /is not a correct/,
    //   "Wrongly formated dates should be invalid"
    // );
    // ---

    assert.equal(parseDate("1197").toFormat(testDateFormat), "01.01/1197");
    assert.equal(parseDate("0131").toFormat(testDateFormat), "01.01/0131");
    assert.throws(
      function () {
        parseDate("970131");
      },
      /is not a correct/,
      "Wrongly formated dates should be invalid"
    );
    assert.equal(parseDate("3101").toFormat(testDateFormat), "31.01/" + DateTime.utc().year);
    assert.equal(parseDate("31.01").toFormat(testDateFormat), "31.01/" + DateTime.utc().year);
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
    assert.equal(parseDateTime("3101198508").toFormat(dateTimeFormat), "31.01/1985 08:00/00");
    assert.equal(parseDateTime("310119850833").toFormat(dateTimeFormat), "31.01/1985 08:33/00");
    assert.equal(parseDateTime("31/01/1985 08").toFormat(dateTimeFormat), "31.01/1985 08:00/00");
    unpatch(localization, "patch loc");
  });

  QUnit.test("parse smart date input", async (assert) => {
    const format = "dd MM yyyy";
    assert.strictEqual(
      parseDate("+1d").toFormat(format),
      DateTime.local().plus({ days: 1 }).toFormat(format)
    );
    assert.strictEqual(
      parseDateTime("+2w").toFormat(format),
      DateTime.local().plus({ weeks: 2 }).toFormat(format)
    );
    assert.strictEqual(
      parseDate("+3m").toFormat(format),
      DateTime.local().plus({ months: 3 }).toFormat(format)
    );
    assert.strictEqual(
      parseDateTime("+4y").toFormat(format),
      DateTime.local().plus({ years: 4 }).toFormat(format)
    );
    assert.strictEqual(
      parseDate("+5").toFormat(format),
      DateTime.local().plus({ days: 5 }).toFormat(format)
    );
    assert.strictEqual(
      parseDateTime("-5").toFormat(format),
      DateTime.local().minus({ days: 5 }).toFormat(format)
    );
    assert.strictEqual(
      parseDate("-4y").toFormat(format),
      DateTime.local().minus({ years: 4 }).toFormat(format)
    );
    assert.strictEqual(
      parseDateTime("-3m").toFormat(format),
      DateTime.local().minus({ months: 3 }).toFormat(format)
    );
    assert.strictEqual(
      parseDate("-2w").toFormat(format),
      DateTime.local().minus({ weeks: 2 }).toFormat(format)
    );
    assert.strictEqual(
      parseDateTime("-1d").toFormat(format),
      DateTime.local().minus({ days: 1 }).toFormat(format)
    );
  });
});
