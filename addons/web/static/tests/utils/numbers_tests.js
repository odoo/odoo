/** @odoo-module **/

import { localization } from "../../src/localization/localization_settings";
import { humanNumber, formatFloat, parseFloat } from "../../src/utils/numbers";
import { patch, unpatch } from "../../src/utils/patch";
import { defaultLocalization } from "../helpers/mock_services";

QUnit.module("utils", () => {
  QUnit.module("numbers");

  QUnit.test("humanNumber", async (assert) => {
    assert.strictEqual(humanNumber(1020, { decimals: 2, minDigits: 1 }), "1.02k");
    assert.strictEqual(humanNumber(1020000, { decimals: 2, minDigits: 2 }), "1020k");
    assert.strictEqual(humanNumber(10200000, { decimals: 2, minDigits: 2 }), "10.2M");
    assert.strictEqual(humanNumber(1020, { decimals: 2, minDigits: 1 }), "1.02k");
    assert.strictEqual(humanNumber(1002, { decimals: 2, minDigits: 1 }), "1k");
    assert.strictEqual(humanNumber(101, { decimals: 2, minDigits: 1 }), "101");
    assert.strictEqual(humanNumber(64.2, { decimals: 2, minDigits: 1 }), "64");
    assert.strictEqual(humanNumber(1e18), "1E");
    assert.strictEqual(humanNumber(1e21, { decimals: 2, minDigits: 1 }), "1e+21");
    assert.strictEqual(humanNumber(1.0045e22, { decimals: 2, minDigits: 1 }), "1e+22");
    assert.strictEqual(humanNumber(1.0045e22, { decimals: 3, minDigits: 1 }), "1.005e+22");
    assert.strictEqual(humanNumber(1.012e43, { decimals: 2, minDigits: 1 }), "1.01e+43");
    assert.strictEqual(humanNumber(1.012e43, { decimals: 2, minDigits: 2 }), "1.01e+43");
    assert.strictEqual(humanNumber(-1020, { decimals: 2, minDigits: 1 }), "-1.02k");
    assert.strictEqual(humanNumber(-1020000, { decimals: 2, minDigits: 2 }), "-1020k");
    assert.strictEqual(humanNumber(-10200000, { decimals: 2, minDigits: 2 }), "-10.2M");
    assert.strictEqual(humanNumber(-1020, { decimals: 2, minDigits: 1 }), "-1.02k");
    assert.strictEqual(humanNumber(-1002, { decimals: 2, minDigits: 1 }), "-1k");
    assert.strictEqual(humanNumber(-101, { decimals: 2, minDigits: 1 }), "-101");
    assert.strictEqual(humanNumber(-64.2, { decimals: 2, minDigits: 1 }), "-64");
    assert.strictEqual(humanNumber(-1e18), "-1E");
    assert.strictEqual(humanNumber(-1e21, { decimals: 2, minDigits: 1 }), "-1e+21");
    assert.strictEqual(humanNumber(-1.0045e22, { decimals: 2, minDigits: 1 }), "-1e+22");
    assert.strictEqual(humanNumber(-1.0045e22, { decimals: 3, minDigits: 1 }), "-1.004e+22");
    assert.strictEqual(humanNumber(-1.012e43, { decimals: 2, minDigits: 1 }), "-1.01e+43");
    assert.strictEqual(humanNumber(-1.012e43, { decimals: 2, minDigits: 2 }), "-1.01e+43");
  });

  QUnit.test("formatFloat", async (assert) => {
    patch(localization, "defaultlocalization", defaultLocalization);

    assert.strictEqual(formatFloat(1000000), "1,000,000.00");

    patch(localization, "weirdgrouping", { grouping: [3, 2, -1] });
    assert.strictEqual(formatFloat(106500), "1,06,500.00");
    unpatch(localization, "weirdgrouping");

    patch(localization, "weirdgrouping", { grouping: [1, 2, -1] });
    assert.strictEqual(formatFloat(106500), "106,50,0.00");
    unpatch(localization, "weirdgrouping");

    patch(localization, "otherlocalization", {
      grouping: [2, 0],
      decimalPoint: "!",
      thousandsSep: "@",
    });
    assert.strictEqual(formatFloat(6000), "60@00!00");
    assert.strictEqual(formatFloat(false), "");
    unpatch(localization, "otherlocalization");

    unpatch(localization, "defaultlocalization");
  });

  QUnit.test("parseFloat", async (assert) => {
    patch(localization, "patch1", { grouping: [3, 0], decimalPoint: ".", thousandsSep: "," });
    assert.strictEqual(parseFloat(""), 0);
    assert.strictEqual(parseFloat("0"), 0);
    assert.strictEqual(parseFloat("100.00"), 100);
    assert.strictEqual(parseFloat("-100.00"), -100);
    assert.strictEqual(parseFloat("1,000.00"), 1000);
    assert.strictEqual(parseFloat("1,000,000.00"), 1000000);
    assert.strictEqual(parseFloat("1,234.567"), 1234.567);
    assert.throws(function () {
      parseFloat("1.000.000");
    }, "Throw an exception if it's not a valid number");
    unpatch(localization, "patch1");

    patch(localization, "patch2", { grouping: [3, 0], decimalPoint: ",", thousandsSep: "." });
    assert.strictEqual(parseFloat("1.234,567"), 1234.567);
    assert.throws(function () {
      parseFloat("1,000,000");
    }, "Throw an exception if it's not a valid number");
    unpatch(localization, "patch2");
  });
});
