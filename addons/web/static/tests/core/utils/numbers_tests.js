/** @odoo-module **/

import { defaultLocalization } from "@web/../tests/helpers/mock_services";
import { patchWithCleanup } from "@web/../tests/helpers/utils";
import { localization } from "@web/core/l10n/localization";

import { roundPrecision, roundDecimals, floatIsZero, formatFloat } from "@web/core/utils/numbers";

QUnit.module("utils", () => {
    QUnit.module("numbers");

    QUnit.test("roundPrecision", function (assert) {
        assert.expect(26);

        assert.strictEqual(String(roundPrecision(1.0, 1)), "1");
        assert.strictEqual(String(roundPrecision(1.0, 0.1)), "1");
        assert.strictEqual(String(roundPrecision(1.0, 0.01)), "1");
        assert.strictEqual(String(roundPrecision(1.0, 0.001)), "1");
        assert.strictEqual(String(roundPrecision(1.0, 0.0001)), "1");
        assert.strictEqual(String(roundPrecision(1.0, 0.00001)), "1");
        assert.strictEqual(String(roundPrecision(1.0, 0.000001)), "1");
        assert.strictEqual(String(roundPrecision(1.0, 0.0000001)), "1");
        assert.strictEqual(String(roundPrecision(1.0, 0.00000001)), "1");
        assert.strictEqual(String(roundPrecision(0.5, 1)), "1");
        assert.strictEqual(String(roundPrecision(-0.5, 1)), "-1");
        assert.strictEqual(String(roundPrecision(2.6745, 0.001)), "2.6750000000000003");
        assert.strictEqual(String(roundPrecision(-2.6745, 0.001)), "-2.6750000000000003");
        assert.strictEqual(String(roundPrecision(2.6744, 0.001)), "2.674");
        assert.strictEqual(String(roundPrecision(-2.6744, 0.001)), "-2.674");
        assert.strictEqual(String(roundPrecision(0.0004, 0.001)), "0");
        assert.strictEqual(String(roundPrecision(-0.0004, 0.001)), "0");
        assert.strictEqual(String(roundPrecision(357.4555, 0.001)), "357.456");
        assert.strictEqual(String(roundPrecision(-357.4555, 0.001)), "-357.456");
        assert.strictEqual(String(roundPrecision(457.4554, 0.001)), "457.455");
        assert.strictEqual(String(roundPrecision(-457.4554, 0.001)), "-457.455");
        assert.strictEqual(String(roundPrecision(-457.4554, 0.05)), "-457.45000000000005");
        assert.strictEqual(String(roundPrecision(457.444, 0.5)), "457.5");
        assert.strictEqual(String(roundPrecision(457.3, 5)), "455");
        assert.strictEqual(String(roundPrecision(457.5, 5)), "460");
        assert.strictEqual(String(roundPrecision(457.1, 3)), "456");
    });

    QUnit.test("roundDecimals", function (assert) {
        assert.expect(21);

        assert.strictEqual(String(roundDecimals(1.0, 0)), "1");
        assert.strictEqual(String(roundDecimals(1.0, 1)), "1");
        assert.strictEqual(String(roundDecimals(1.0, 2)), "1");
        assert.strictEqual(String(roundDecimals(1.0, 3)), "1");
        assert.strictEqual(String(roundDecimals(1.0, 4)), "1");
        assert.strictEqual(String(roundDecimals(1.0, 5)), "1");
        assert.strictEqual(String(roundDecimals(1.0, 6)), "1");
        assert.strictEqual(String(roundDecimals(1.0, 7)), "1");
        assert.strictEqual(String(roundDecimals(1.0, 8)), "1");
        assert.strictEqual(String(roundDecimals(0.5, 0)), "1");
        assert.strictEqual(String(roundDecimals(-0.5, 0)), "-1");
        assert.strictEqual(String(roundDecimals(2.6745, 3)), "2.6750000000000003");
        assert.strictEqual(String(roundDecimals(-2.6745, 3)), "-2.6750000000000003");
        assert.strictEqual(String(roundDecimals(2.6744, 3)), "2.674");
        assert.strictEqual(String(roundDecimals(-2.6744, 3)), "-2.674");
        assert.strictEqual(String(roundDecimals(0.0004, 3)), "0");
        assert.strictEqual(String(roundDecimals(-0.0004, 3)), "0");
        assert.strictEqual(String(roundDecimals(357.4555, 3)), "357.456");
        assert.strictEqual(String(roundDecimals(-357.4555, 3)), "-357.456");
        assert.strictEqual(String(roundDecimals(457.4554, 3)), "457.455");
        assert.strictEqual(String(roundDecimals(-457.4554, 3)), "-457.455");
    });

    QUnit.test("floatIsZero", function (assert) {
        assert.strictEqual(floatIsZero(1, 0), false);
        assert.strictEqual(floatIsZero(0.9999, 0), false);
        assert.strictEqual(floatIsZero(0.50001, 0), false);
        assert.strictEqual(floatIsZero(0.5, 0), false);
        assert.strictEqual(floatIsZero(0.49999, 0), true);
        assert.strictEqual(floatIsZero(0, 0), true);
        assert.strictEqual(floatIsZero(0.49999, 0), true);
        assert.strictEqual(floatIsZero(-0.50001, 0), false);
        assert.strictEqual(floatIsZero(-0.5, 0), false);
        assert.strictEqual(floatIsZero(-0.9999, 0), false);
        assert.strictEqual(floatIsZero(-1, 0), false);

        assert.strictEqual(floatIsZero(0.1, 1), false);
        assert.strictEqual(floatIsZero(0.099999, 1), false);
        assert.strictEqual(floatIsZero(0.050001, 1), false);
        assert.strictEqual(floatIsZero(0.05, 1), false);
        assert.strictEqual(floatIsZero(0.049999, 1), true);
        assert.strictEqual(floatIsZero(0, 1), true);
        assert.strictEqual(floatIsZero(-0.049999, 1), true);
        assert.strictEqual(floatIsZero(-0.05, 1), false);
        assert.strictEqual(floatIsZero(-0.050001, 1), false);
        assert.strictEqual(floatIsZero(-0.099999, 1), false);
        assert.strictEqual(floatIsZero(-0.1, 1), false);

        assert.strictEqual(floatIsZero(0.01, 2), false);
        assert.strictEqual(floatIsZero(0.0099999, 2), false);
        assert.strictEqual(floatIsZero(0.005, 2), false);
        assert.strictEqual(floatIsZero(0.0050001, 2), false);
        assert.strictEqual(floatIsZero(0.0049999, 2), true);
        assert.strictEqual(floatIsZero(0, 2), true);
        assert.strictEqual(floatIsZero(-0.0049999, 2), true);
        assert.strictEqual(floatIsZero(-0.0050001, 2), false);
        assert.strictEqual(floatIsZero(-0.005, 2), false);
        assert.strictEqual(floatIsZero(-0.0099999, 2), false);
        assert.strictEqual(floatIsZero(-0.01, 2), false);

        // 4 and 5 decimal places are mentioned as special cases in `roundDecimals` method.
        assert.strictEqual(floatIsZero(0.0001, 4), false);
        assert.strictEqual(floatIsZero(0.000099999, 4), false);
        assert.strictEqual(floatIsZero(0.00005, 4), false);
        assert.strictEqual(floatIsZero(0.000050001, 4), false);
        assert.strictEqual(floatIsZero(0.000049999, 4), true);
        assert.strictEqual(floatIsZero(0, 4), true);
        assert.strictEqual(floatIsZero(-0.000049999, 4), true);
        assert.strictEqual(floatIsZero(-0.000050001, 4), false);
        assert.strictEqual(floatIsZero(-0.00005, 4), false);
        assert.strictEqual(floatIsZero(-0.000099999, 4), false);
        assert.strictEqual(floatIsZero(-0.0001, 4), false);

        assert.strictEqual(floatIsZero(0.00001, 5), false);
        assert.strictEqual(floatIsZero(0.0000099999, 5), false);
        assert.strictEqual(floatIsZero(0.000005, 5), false);
        assert.strictEqual(floatIsZero(0.0000050001, 5), false);
        assert.strictEqual(floatIsZero(0.0000049999, 5), true);
        assert.strictEqual(floatIsZero(0, 5), true);
        assert.strictEqual(floatIsZero(-0.0000049999, 5), true);
        assert.strictEqual(floatIsZero(-0.0000050001, 5), false);
        assert.strictEqual(floatIsZero(-0.000005, 5), false);
        assert.strictEqual(floatIsZero(-0.0000099999, 5), false);
        assert.strictEqual(floatIsZero(-0.00001, 5), false);

        assert.strictEqual(floatIsZero(0.0000001, 7), false);
        assert.strictEqual(floatIsZero(0.000000099999, 7), false);
        assert.strictEqual(floatIsZero(0.00000005, 7), false);
        assert.strictEqual(floatIsZero(0.000000050001, 7), false);
        assert.strictEqual(floatIsZero(0.000000049999, 7), true);
        assert.strictEqual(floatIsZero(0, 7), true);
        assert.strictEqual(floatIsZero(-0.000000049999, 7), true);
        assert.strictEqual(floatIsZero(-0.000000050001, 7), false);
        assert.strictEqual(floatIsZero(-0.00000005, 7), false);
        assert.strictEqual(floatIsZero(-0.000000099999, 7), false);
        assert.strictEqual(floatIsZero(-0.0000001, 7), false);
    });
});

QUnit.module("utils", (hooks) => {
    hooks.beforeEach(() => {
        patchWithCleanup(localization, { ...defaultLocalization, grouping: [3, 0] });
    });

    QUnit.module("numbers");

    QUnit.test("formatFloat", function (assert) {
        assert.strictEqual(formatFloat(1000000), "1,000,000.00");

        const options = { grouping: [3, 2, -1], decimalPoint: "?", thousandsSep: "€" };
        assert.strictEqual(formatFloat(106500, options), "1€06€500?00");

        assert.strictEqual(formatFloat(1500, { thousandsSep: "" }), "1500.00");
        assert.strictEqual(formatFloat(-1.01), "-1.01");
        assert.strictEqual(formatFloat(-0.01), "-0.01");

        assert.strictEqual(formatFloat(38.0001, { trailingZeros: false }), "38");
        assert.strictEqual(formatFloat(38.1, { trailingZeros: false }), "38.1");
        assert.strictEqual(formatFloat(38.0001, { digits: [16, 0], trailingZeros: false }), "38");

        patchWithCleanup(localization, { grouping: [3, 3, 3, 3] });
        assert.strictEqual(formatFloat(1000000), "1,000,000.00");

        patchWithCleanup(localization, { grouping: [3, 2, -1] });
        assert.strictEqual(formatFloat(106500), "1,06,500.00");

        patchWithCleanup(localization, { grouping: [1, 2, -1] });
        assert.strictEqual(formatFloat(106500), "106,50,0.00");

        patchWithCleanup(localization, {
            grouping: [2, 0],
            decimalPoint: "!",
            thousandsSep: "@",
        });
        assert.strictEqual(formatFloat(6000), "60@00!00");
    });

    QUnit.test("formatFloat (humanReadable=true)", async (assert) => {
        assert.strictEqual(
            formatFloat(1020, { humanReadable: true, decimals: 2, minDigits: 1 }),
            "1.02k"
        );
        assert.strictEqual(
            formatFloat(1020000, { humanReadable: true, decimals: 2, minDigits: 2 }),
            "1,020k"
        );
        assert.strictEqual(
            formatFloat(10200000, { humanReadable: true, decimals: 2, minDigits: 2 }),
            "10.20M"
        );
        assert.strictEqual(
            formatFloat(1020, { humanReadable: true, decimals: 2, minDigits: 1 }),
            "1.02k"
        );
        assert.strictEqual(
            formatFloat(1002, { humanReadable: true, decimals: 2, minDigits: 1 }),
            "1.00k"
        );
        assert.strictEqual(
            formatFloat(101, { humanReadable: true, decimals: 2, minDigits: 1 }),
            "101.00"
        );
        assert.strictEqual(
            formatFloat(64.2, { humanReadable: true, decimals: 2, minDigits: 1 }),
            "64.20"
        );
        assert.strictEqual(formatFloat(1e18, { humanReadable: true }), "1E");
        assert.strictEqual(
            formatFloat(1e21, { humanReadable: true, decimals: 2, minDigits: 1 }),
            "1e+21"
        );
        assert.strictEqual(
            formatFloat(1.0045e22, { humanReadable: true, decimals: 2, minDigits: 1 }),
            "1e+22"
        );
        assert.strictEqual(
            formatFloat(1.0045e22, { humanReadable: true, decimals: 3, minDigits: 1 }),
            "1.005e+22"
        );
        assert.strictEqual(
            formatFloat(1.012e43, { humanReadable: true, decimals: 2, minDigits: 1 }),
            "1.01e+43"
        );
        assert.strictEqual(
            formatFloat(1.012e43, { humanReadable: true, decimals: 2, minDigits: 2 }),
            "1.01e+43"
        );
        assert.strictEqual(
            formatFloat(-1020, { humanReadable: true, decimals: 2, minDigits: 1 }),
            "-1.02k"
        );
        assert.strictEqual(
            formatFloat(-1020000, { humanReadable: true, decimals: 2, minDigits: 2 }),
            "-1,020k"
        );
        assert.strictEqual(
            formatFloat(-10200000, { humanReadable: true, decimals: 2, minDigits: 2 }),
            "-10.20M"
        );
        assert.strictEqual(
            formatFloat(-1020, { humanReadable: true, decimals: 2, minDigits: 1 }),
            "-1.02k"
        );
        assert.strictEqual(
            formatFloat(-1002, { humanReadable: true, decimals: 2, minDigits: 1 }),
            "-1.00k"
        );
        assert.strictEqual(
            formatFloat(-101, { humanReadable: true, decimals: 2, minDigits: 1 }),
            "-101.00"
        );
        assert.strictEqual(
            formatFloat(-64.2, { humanReadable: true, decimals: 2, minDigits: 1 }),
            "-64.20"
        );
        assert.strictEqual(formatFloat(-1e18, { humanReadable: true }), "-1E");
        assert.strictEqual(
            formatFloat(-1e21, { humanReadable: true, decimals: 2, minDigits: 1 }),
            "-1e+21"
        );
        assert.strictEqual(
            formatFloat(-1.0045e22, { humanReadable: true, decimals: 2, minDigits: 1 }),
            "-1e+22"
        );
        assert.strictEqual(
            formatFloat(-1.0045e22, { humanReadable: true, decimals: 3, minDigits: 1 }),
            "-1.004e+22"
        );
        assert.strictEqual(
            formatFloat(-1.012e43, { humanReadable: true, decimals: 2, minDigits: 1 }),
            "-1.01e+43"
        );
        assert.strictEqual(
            formatFloat(-1.012e43, { humanReadable: true, decimals: 2, minDigits: 2 }),
            "-1.01e+43"
        );
    });
});
