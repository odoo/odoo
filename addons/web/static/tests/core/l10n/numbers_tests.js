/** @odoo-module **/

import { defaultLocalization } from "@web/../tests/helpers/mock_services";
import { formatFloat, humanNumber, parseFloat } from "@web/core/l10n/numbers";
import { localization } from "@web/core/l10n/localization";
import { patchWithCleanup } from "@web/../tests/helpers/utils";

QUnit.module("utils", (hooks) => {
    hooks.beforeEach(async () => {
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
        assert.throws(
            () => parseFloat("1.000.000"),
            "Throw an exception if it's not a valid number"
        );

        patchWithCleanup(localization, { decimalPoint: ",", thousandsSep: "." });
        assert.strictEqual(parseFloat("1.234,567"), 1234.567);
        assert.throws(
            () => parseFloat("1,000,000"),
            "Throw an exception if it's not a valid number"
        );
    });
});
