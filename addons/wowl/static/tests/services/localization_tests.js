/** @odoo-module **/
import { useService } from "../../src/core/hooks";
import { getFixture, makeTestEnv, mount } from "../helpers/index";
import { Registry } from "../../src/core/registry";
import { makeFakeLocalizationService } from "../helpers/mocks";
const { DateTime, Settings } = luxon;
const terms = { Hello: "Bonjour" };
class TestComponent extends owl.Component {}
const makeTestLocalizationEnv = async (config) => {
  const serviceRegistry = new Registry();
  serviceRegistry.add("localization", makeFakeLocalizationService(config));
  return await makeTestEnv({ serviceRegistry });
};
QUnit.module("Localization");
QUnit.test("can translate a text node", async (assert) => {
  assert.expect(1);
  TestComponent.template = owl.tags.xml`<div>Hello</div>`;
  const env = await makeTestLocalizationEnv({ terms });
  const target = getFixture();
  await mount(TestComponent, { env, target });
  assert.strictEqual(target.innerText, "Bonjour");
});
QUnit.test("_t can be found in component env", async (assert) => {
  assert.expect(1);
  TestComponent.template = owl.tags.xml`<span t-esc="env._t('Hello')"/>`;
  const env = await makeTestLocalizationEnv({ terms });
  const target = getFixture();
  await mount(TestComponent, { env, target });
  assert.strictEqual(target.innerText, "Bonjour");
});
QUnit.test("components can access lang parameters", async (assert) => {
  assert.expect(1);
  class TestComponent extends owl.Component {
    constructor() {
      super(...arguments);
      this.localizationService = useService("localization");
      this.decimalPoint = this.localizationService.decimalPoint;
    }
  }
  TestComponent.template = owl.tags.xml`<span t-esc="decimalPoint"/>`;
  const decimalPoint = ",";
  const env = await makeTestLocalizationEnv({ langParams: { decimalPoint } });
  const target = getFixture();
  await mount(TestComponent, { env, target });
  assert.strictEqual(target.innerText, decimalPoint);
});
QUnit.test("formatDateTime", async (assert) => {
  const { localization: l10n } = (await makeTestEnv()).services;
  // const isoDateStr = "2009-05-04 12:34:23"; // with moment, this one was accepted as an iso date string
  const isoDateStr = "2009-05-04T12:34:23";
  const date = l10n.parseDateTime(isoDateStr);
  const str = l10n.formatDateTime(date, { timezone: false });
  assert.strictEqual(str, date.toFormat("MM/dd/yyyy HH:mm:ss"));
});
QUnit.test("formatDateTime (with different timezone offset)", async (assert) => {
  // BOI: with legacy web, date format was mocked but IMHO this is not needed here.
  const env = await makeTestLocalizationEnv({ langParams: { dateFormat: "%m/%d/%Y" } });
  const { localization: l10n } = env.services;
  let str = l10n.formatDateTime(DateTime.utc(2017, 1, 1, 10, 0, 0, 0));
  assert.strictEqual(str, "01/01/2017 11:00:00");
  str = l10n.formatDateTime(DateTime.utc(2017, 6, 1, 10, 0, 0, 0));
  assert.strictEqual(str, "06/01/2017 12:00:00");
});
QUnit.test("formatFloat", async (assert) => {
  const env1 = await makeTestLocalizationEnv({ langParams: { grouping: [3, 3, 3, 3] } });
  const env2 = await makeTestLocalizationEnv({ langParams: { grouping: [3, 2, -1] } });
  const env3 = await makeTestLocalizationEnv({ langParams: { grouping: [1, 2, -1] } });
  const env4 = await makeTestLocalizationEnv({
    langParams: { grouping: [3, 0], decimalPoint: ",", thousandsSep: "." },
  });
  let l10n = env1.services.localization;
  assert.strictEqual(l10n.formatFloat(1000000), "1,000,000.00");
  l10n = env2.services.localization;
  assert.strictEqual(l10n.formatFloat(106500), "1,06,500.00");
  l10n = env3.services.localization;
  assert.strictEqual(l10n.formatFloat(106500), "106,50,0.00");
  l10n = env4.services.localization;
  assert.strictEqual(l10n.formatFloat(6000), "6.000,00");
  assert.strictEqual(l10n.formatFloat(false), "");
});
QUnit.test("humanNumber", async (assert) => {
  const { localization: l10n } = (await makeTestEnv()).services;
  assert.strictEqual(l10n.humanNumber(1020, { decimals: 2, minDigits: 1 }), "1.02k");
  assert.strictEqual(l10n.humanNumber(1020000, { decimals: 2, minDigits: 2 }), "1020k");
  assert.strictEqual(l10n.humanNumber(10200000, { decimals: 2, minDigits: 2 }), "10.2M");
  assert.strictEqual(l10n.humanNumber(1020, { decimals: 2, minDigits: 1 }), "1.02k");
  assert.strictEqual(l10n.humanNumber(1002, { decimals: 2, minDigits: 1 }), "1k");
  assert.strictEqual(l10n.humanNumber(101, { decimals: 2, minDigits: 1 }), "101");
  assert.strictEqual(l10n.humanNumber(64.2, { decimals: 2, minDigits: 1 }), "64");
  assert.strictEqual(l10n.humanNumber(1e18), "1E");
  assert.strictEqual(l10n.humanNumber(1e21, { decimals: 2, minDigits: 1 }), "1e+21");
  assert.strictEqual(l10n.humanNumber(1.0045e22, { decimals: 2, minDigits: 1 }), "1e+22");
  assert.strictEqual(l10n.humanNumber(1.0045e22, { decimals: 3, minDigits: 1 }), "1.005e+22");
  assert.strictEqual(l10n.humanNumber(1.012e43, { decimals: 2, minDigits: 1 }), "1.01e+43");
  assert.strictEqual(l10n.humanNumber(1.012e43, { decimals: 2, minDigits: 2 }), "1.01e+43");
  assert.strictEqual(l10n.humanNumber(-1020, { decimals: 2, minDigits: 1 }), "-1.02k");
  assert.strictEqual(l10n.humanNumber(-1020000, { decimals: 2, minDigits: 2 }), "-1020k");
  assert.strictEqual(l10n.humanNumber(-10200000, { decimals: 2, minDigits: 2 }), "-10.2M");
  assert.strictEqual(l10n.humanNumber(-1020, { decimals: 2, minDigits: 1 }), "-1.02k");
  assert.strictEqual(l10n.humanNumber(-1002, { decimals: 2, minDigits: 1 }), "-1k");
  assert.strictEqual(l10n.humanNumber(-101, { decimals: 2, minDigits: 1 }), "-101");
  assert.strictEqual(l10n.humanNumber(-64.2, { decimals: 2, minDigits: 1 }), "-64");
  assert.strictEqual(l10n.humanNumber(-1e18), "-1E");
  assert.strictEqual(l10n.humanNumber(-1e21, { decimals: 2, minDigits: 1 }), "-1e+21");
  assert.strictEqual(l10n.humanNumber(-1.0045e22, { decimals: 2, minDigits: 1 }), "-1e+22");
  assert.strictEqual(l10n.humanNumber(-1.0045e22, { decimals: 3, minDigits: 1 }), "-1.004e+22");
  assert.strictEqual(l10n.humanNumber(-1.012e43, { decimals: 2, minDigits: 1 }), "-1.01e+43");
  assert.strictEqual(l10n.humanNumber(-1.012e43, { decimals: 2, minDigits: 2 }), "-1.01e+43");
});
QUnit.test("parseDateTime", async (assert) => {
  const env = await makeTestLocalizationEnv({
    langParams: { dateFormat: "%m/%d/%Y", timeFormat: "%H:%M:%S" },
  });
  const { localization: l10n } = env.services;
  assert.throws(
    function () {
      l10n.parseDateTime("13/01/2019 12:00:00");
    },
    /is not a correct/,
    "Wrongly formated dates should be invalid"
  );
  assert.throws(
    function () {
      l10n.parseDateTime("01/01/10000 12:00:00");
    },
    /is not a correct/,
    "Dates after 9999 should be invalid"
  );
  let dateStr = "01/13/2019 10:05:45";
  let date1 = l10n.parseDateTime(dateStr);
  let date2 = DateTime.fromFormat(dateStr, "MM/dd/yyyy HH:mm:ss");
  assert.equal(date1.toISO(), date2.toISO(), "Date with leading 0");
  dateStr = "1/13/2019 10:5:45";
  date1 = l10n.parseDateTime(dateStr);
  date2 = DateTime.fromFormat(dateStr, "M/d/yyyy H:m:s");
  assert.equal(date1.toISO(), date2.toISO(), "Date without leading 0");
  dateStr = "01/01/0001 10:15:45";
  date1 = l10n.parseDateTime(dateStr);
  date2 = DateTime.fromFormat(dateStr, "MM/dd/yyyy HH:mm:ss");
  assert.equal(date1.toISO(), date2.toISO(), "can parse dates of year 1");
  dateStr = "1/1/1 10:15:45";
  date1 = l10n.parseDateTime(dateStr);
  date2 = DateTime.fromFormat(dateStr, "M/d/y H:m:s");
  assert.equal(date1.toISO(), date2.toISO(), "can parse dates of year 1");
});
QUnit.test("parseDateTime (norwegian locale)", async (assert) => {
  const env = await makeTestLocalizationEnv({
    langParams: { dateFormat: "%d. %b %Y", timeFormat: "%H:%M:%S" },
  });
  const { localization: l10n } = env.services;
  // Before WOWL we were using MomentJS.
  // Now it has been replaced by luxon.js, we cannot declare customized locales.
  // In legacy web, parseDateTime tests were originally defining custom locales
  // for english and norwegian.
  // Here, we simply use the vanilla Intl support to switch locale.
  const originalLocale = Settings.defaultLocale;
  Settings.defaultLocale = "no"; // Norwegian
  const dateStr = "16. des 2019 10:05:45";
  const date1 = l10n.parseDateTime(dateStr);
  const date2 = DateTime.fromFormat(dateStr, "d. MMM y H:m:s");
  assert.equal(date1.toISO(), date2.toISO(), "Day/month inverted + month i18n");
  Settings.defaultLocale = originalLocale;
});
QUnit.test("parseDate without separator", async (assert) => {
  const env = await makeTestLocalizationEnv({ langParams: { dateFormat: "%d.%m/%Y" } });
  const { localization: l10n } = env.services;
  const dateFormat = "dd.MM/yyyy";
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
  assert.equal(l10n.parseDate("1197").toFormat(dateFormat), "01.01/1197");
  assert.equal(l10n.parseDate("0131").toFormat(dateFormat), "01.01/0131");
  assert.throws(
    function () {
      l10n.parseDate("970131");
    },
    /is not a correct/,
    "Wrongly formated dates should be invalid"
  );
  assert.equal(l10n.parseDate("3101").toFormat(dateFormat), "31.01/" + DateTime.utc().year);
  assert.equal(l10n.parseDate("31.01").toFormat(dateFormat), "31.01/" + DateTime.utc().year);
  assert.equal(l10n.parseDate("310197").toFormat(dateFormat), "31.01/1997");
  assert.equal(l10n.parseDate("310117").toFormat(dateFormat), "31.01/2017");
  assert.equal(l10n.parseDate("31011985").toFormat(dateFormat), "31.01/1985");
});
QUnit.test("parseDateTime without separator", async (assert) => {
  const env = await makeTestLocalizationEnv({
    langParams: { dateFormat: "%d.%m/%Y", timeFormat: "%H:%M/%S" },
  });
  const { localization: l10n } = env.services;
  const dateTimeFormat = "dd.MM/yyyy HH:mm/ss";
  assert.equal(l10n.parseDateTime("3101198508").toFormat(dateTimeFormat), "31.01/1985 08:00/00");
  assert.equal(l10n.parseDateTime("310119850833").toFormat(dateTimeFormat), "31.01/1985 08:33/00");
  assert.equal(l10n.parseDateTime("31/01/1985 08").toFormat(dateTimeFormat), "31.01/1985 08:00/00");
});
QUnit.test("parse smart date input", async (assert) => {
  const { localization: l10n } = (await makeTestEnv()).services;
  const format = "dd MM yyyy";
  assert.strictEqual(
    l10n.parseDate("+1d").toFormat(format),
    DateTime.local().plus({ days: 1 }).toFormat(format)
  );
  assert.strictEqual(
    l10n.parseDateTime("+2w").toFormat(format),
    DateTime.local().plus({ weeks: 2 }).toFormat(format)
  );
  assert.strictEqual(
    l10n.parseDate("+3m").toFormat(format),
    DateTime.local().plus({ months: 3 }).toFormat(format)
  );
  assert.strictEqual(
    l10n.parseDateTime("+4y").toFormat(format),
    DateTime.local().plus({ years: 4 }).toFormat(format)
  );
  assert.strictEqual(
    l10n.parseDate("+5").toFormat(format),
    DateTime.local().plus({ days: 5 }).toFormat(format)
  );
  assert.strictEqual(
    l10n.parseDateTime("-5").toFormat(format),
    DateTime.local().minus({ days: 5 }).toFormat(format)
  );
  assert.strictEqual(
    l10n.parseDate("-4y").toFormat(format),
    DateTime.local().minus({ years: 4 }).toFormat(format)
  );
  assert.strictEqual(
    l10n.parseDateTime("-3m").toFormat(format),
    DateTime.local().minus({ months: 3 }).toFormat(format)
  );
  assert.strictEqual(
    l10n.parseDate("-2w").toFormat(format),
    DateTime.local().minus({ weeks: 2 }).toFormat(format)
  );
  assert.strictEqual(
    l10n.parseDateTime("-1d").toFormat(format),
    DateTime.local().minus({ days: 1 }).toFormat(format)
  );
});
QUnit.test("parseFloat", async (assert) => {
  const env1 = await makeTestLocalizationEnv({
    langParams: { grouping: [3, 0], decimalPoint: ".", thousandsSep: "," },
  });
  const env2 = await makeTestLocalizationEnv({
    langParams: { grouping: [3, 0], decimalPoint: ",", thousandsSep: "." },
  });
  let l10n = env1.services.localization;
  assert.strictEqual(l10n.parseFloat(""), 0);
  assert.strictEqual(l10n.parseFloat("0"), 0);
  assert.strictEqual(l10n.parseFloat("100.00"), 100);
  assert.strictEqual(l10n.parseFloat("-100.00"), -100);
  assert.strictEqual(l10n.parseFloat("1,000.00"), 1000);
  assert.strictEqual(l10n.parseFloat("1,000,000.00"), 1000000);
  assert.strictEqual(l10n.parseFloat("1,234.567"), 1234.567);
  assert.throws(function () {
    l10n.parseFloat("1.000.000");
  }, "Throw an exception if it's not a valid number");
  l10n = env2.services.localization;
  assert.strictEqual(l10n.parseFloat("1.234,567"), 1234.567);
  assert.throws(function () {
    l10n.parseFloat("1,000,000");
  }, "Throw an exception if it's not a valid number");
});
