/** @odoo-module **/

import { defaultLocalization } from "../../helpers/mock_services";
import {
    formatFloat,
    humanNumber,
    parseFloat,
    parseFloatTime,
    parseInteger,
    parsePercentage,
} from "@web/core/l10n/numbers";
import { localization } from "@web/core/l10n/localization";
import { patchWithCleanup } from "@web/../tests/helpers/utils";

function expectInvalidNumberError(assert, func, value, options) {
    let message = `${func.name} fails on value: "${value}"`;
    if (options) {
        message += ` with options: ${JSON.stringify(options)}`;
    }
    assert.throws(() => func(value, options), message);
}

QUnit.module("utils", (hooks) => {
    hooks.beforeEach(() => {
        patchWithCleanup(localization, defaultLocalization);
    });

    QUnit.module("numbers");

    QUnit.test("formatFloat", async (assert) => {
        assert.expect(5);

        assert.strictEqual(formatFloat(1000000), "1,000,000.00");

        patchWithCleanup(localization, { grouping: [3, 2, -1] });
        assert.strictEqual(formatFloat(106500), "1,06,500.00");

        patchWithCleanup(localization, { grouping: [1, 2, -1] });
        assert.strictEqual(formatFloat(106500), "106,50,0.00");

        patchWithCleanup(localization, { grouping: [2, 0], decimalPoint: "!", thousandsSep: "@" });
        assert.strictEqual(formatFloat(6000), "60@00!00");
        assert.strictEqual(formatFloat(false), "");
    });

    QUnit.test("humanNumber", async (assert) => {
        assert.expect(26);

        assert.strictEqual(humanNumber(1020, { decimals: 2, minDigits: 1 }), "1.02k");
        assert.strictEqual(humanNumber(1020000, { decimals: 2, minDigits: 2 }), "1,020k");
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
        assert.strictEqual(humanNumber(-1020000, { decimals: 2, minDigits: 2 }), "-1,020k");
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

    QUnit.test("parseFloat", async (assert) => {
        assert.expect(10);

        assert.strictEqual(parseFloat(""), 0);
        assert.strictEqual(parseFloat("0"), 0);
        assert.strictEqual(parseFloat("100.00"), 100);
        assert.strictEqual(parseFloat("-100.00"), -100);
        assert.strictEqual(parseFloat("1,000.00"), 1000);
        assert.strictEqual(parseFloat("1,000,000.00"), 1000000);
        assert.strictEqual(parseFloat("1,234.567"), 1234.567);
        expectInvalidNumberError(assert, parseFloat, "1.000.000");

        patchWithCleanup(localization, { decimalPoint: ",", thousandsSep: "." });
        assert.strictEqual(parseFloat("1.234,567"), 1234.567);
        expectInvalidNumberError(assert, parseFloat, "1,000,000");
    });

    QUnit.test("parseFloatTime", function (assert) {
        assert.expect(12);

        assert.strictEqual(parseFloatTime("0"), 0);
        assert.strictEqual(parseFloatTime("100"), 100);
        assert.strictEqual(parseFloatTime("100.00"), 100);
        assert.strictEqual(parseFloatTime("7:15"), 7.25);
        assert.strictEqual(parseFloatTime("-4:30"), -4.5);
        assert.strictEqual(parseFloatTime(":"), 0);
        assert.strictEqual(parseFloatTime("1:"), 1);
        assert.strictEqual(parseFloatTime(":12"), 0.2);

        expectInvalidNumberError(assert, parseFloatTime, "a:1");
        expectInvalidNumberError(assert, parseFloatTime, "1:a");
        expectInvalidNumberError(assert, parseFloatTime, "1:1:");
        expectInvalidNumberError(assert, parseFloatTime, ":1:1");
    });

    QUnit.test("parseInteger", function (assert) {
        assert.expect(11);

        assert.strictEqual(parseInteger(""), 0);
        assert.strictEqual(parseInteger("0"), 0);
        assert.strictEqual(parseInteger("100"), 100);
        assert.strictEqual(parseInteger("-100"), -100);
        assert.strictEqual(parseInteger("1,000"), 1000);
        assert.strictEqual(parseInteger("1,000,000"), 1000000);
        expectInvalidNumberError(assert, parseInteger, "1.000.000");
        expectInvalidNumberError(assert, parseInteger, "1,234.567");

        patchWithCleanup(localization, { decimalPoint: ",", thousandsSep: "." });

        assert.strictEqual(parseInteger("1.000.000"), 1000000);
        expectInvalidNumberError(assert, parseInteger, "1,000,000");
        expectInvalidNumberError(assert, parseInteger, "1.234,567");
    });

    QUnit.test("parsePercentage", function (assert) {
        assert.expect(9);

        assert.strictEqual(parsePercentage(""), 0);
        assert.strictEqual(parsePercentage("0"), 0);
        assert.strictEqual(parsePercentage("0.5"), 0.005);
        assert.strictEqual(parsePercentage("1"), 0.01);
        assert.strictEqual(parsePercentage("100"), 1);
        assert.strictEqual(parsePercentage("50%"), 0.5);
        expectInvalidNumberError(assert, parsePercentage, "50%40");

        patchWithCleanup(localization, { decimalPoint: ",", thousandsSep: "." });

        assert.strictEqual(parsePercentage("1.234,56"), 12.3456);
        assert.strictEqual(parsePercentage("6,02"), 0.0602);
    });
});
