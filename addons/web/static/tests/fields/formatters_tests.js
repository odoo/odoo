/** @odoo-module **/

import { localization } from "@web/core/l10n/localization";
import {
    formatFloat,
    formatFloatFactor,
    formatFloatTime,
    formatInteger,
    formatMany2one,
    formatMonetary,
    formatPercentage,
} from "@web/fields/formatters";
import { defaultLocalization } from "../helpers/mock_services";
import { patchWithCleanup } from "../helpers/utils";
import { session } from "@web/session";

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
        patchWithCleanup(localization, defaultLocalization);
    });

    QUnit.module("Formatters");

    QUnit.test("formatFloat", function (assert) {
        assert.strictEqual(formatFloat(false), "");
        assert.strictEqual(formatFloat(null), '0.00');
        assert.strictEqual(formatFloat(1000000), "1,000,000.00");

        let options = { grouping: [3, 2, -1], decimalPoint: "?", thousandsSep: "€" };
        assert.strictEqual(formatFloat(106500, options), "1€06€500?00");

        assert.strictEqual(formatFloat(1500, { thousandsSep: "" }), "1500.00");

        assert.strictEqual(formatFloat(38.0001, { noTrailingZeros: true }), "38");
        assert.strictEqual(formatFloat(38.1, { noTrailingZeros: true }), "38.1");

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

    QUnit.test("formatFloatFactor", function (assert) {
        assert.strictEqual(formatFloatFactor(false), "");
        assert.strictEqual(formatFloatFactor(6000), "6,000.00");
        assert.strictEqual(formatFloatFactor(6000, { factor: 3 }), "18,000.00");
        assert.strictEqual(formatFloatFactor(6000, { factor: 0.5 }), "3,000.00");
    });

    QUnit.test("formatFloatTime", function (assert) {
        assert.strictEqual(formatFloatTime(2), "02:00");
        assert.strictEqual(formatFloatTime(3.5), "03:30");
        assert.strictEqual(formatFloatTime(0.25), "00:15");

        assert.strictEqual(formatFloatTime(-0.5), "-00:30");

        const options = { noLeadingZeroHour: true };
        assert.strictEqual(formatFloatTime(2, options), "2:00");
        assert.strictEqual(formatFloatTime(3.5, options), "3:30");
        assert.strictEqual(formatFloatTime(-0.5, options), "-0:30");
    });

    QUnit.test("formatInteger", function (assert) {
        assert.strictEqual(formatInteger(false), "");
        assert.strictEqual(formatInteger(0), "0");

        patchWithCleanup(localization, { grouping: [3, 3, 3, 3] });
        assert.strictEqual(formatInteger(1000000), "1,000,000");

        patchWithCleanup(localization, { grouping: [3, 2, -1] });
        assert.strictEqual(formatInteger(106500), "1,06,500");

        patchWithCleanup(localization, { grouping: [1, 2, -1] });
        assert.strictEqual(formatInteger(106500), "106,50,0");

        const options = { grouping: [2, 0], thousandsSep: "€" };
        assert.strictEqual(formatInteger(6000, options), "60€00");
    });

    QUnit.test("formatMany2one", function (assert) {
        assert.strictEqual(formatMany2one(null), "");
        assert.strictEqual(formatMany2one([1, "A M2O value"]), "A M2O value");

        let value = {
            data: { display_name: "A M2O value" },
        };
        assert.strictEqual(formatMany2one(value), "A M2O value");

        value = [1, "A M2O value"];
        assert.strictEqual(formatMany2one(value, { escape: true }), "A%20M2O%20value");

        value = {
            data: { display_name: "A M2O value" },
        };
        assert.strictEqual(formatMany2one(value, { escape: true }), "A%20M2O%20value");
    });

    QUnit.test("formatMonetary", function (assert) {
        patchWithCleanup(session.currencies, {
            10: {
                digits: [69, 2],
                position: "after",
                symbol: "€",
            },
            11: {
                digits: [69, 2],
                position: "before",
                symbol: "$",
            },
            12: {
                digits: [69, 2],
                position: "after",
                symbol: "&",
            },
        });

        assert.strictEqual(formatMonetary(false), "");
        assert.strictEqual(formatMonetary(200), "200.00");

        assert.deepEqual(formatMonetary(1234567.654, { currencyId: 10 }), "1,234,567.65 €");
        assert.deepEqual(formatMonetary(1234567.654, { currencyId: 11 }), "$ 1,234,567.65");
        assert.deepEqual(formatMonetary(1234567.654, { currencyId: 44 }), "1,234,567.65");
        assert.deepEqual(
            formatMonetary(1234567.654, { currencyId: 10, noSymbol: true }),
            "1,234,567.65"
        );
        assert.deepEqual(formatMonetary(8.0, { currencyId: 10, humanReadable: true }), "8.00 €");
        assert.deepEqual(
            formatMonetary(1234567.654, { currencyId: 10, humanReadable: true }),
            "1.23M €"
        );
        assert.deepEqual(
            formatMonetary(1990000.001, { currencyId: 10, humanReadable: true }),
            "1.99M €"
        );
        assert.deepEqual(
            formatMonetary(1234567.654, { currencyId: 44, digits: [69, 1] }),
            "1,234,567.7"
        );
        assert.deepEqual(
            formatMonetary(1234567.654, { currencyId: 11, digits: [69, 1] }),
            "$ 1,234,567.65",
            "currency digits should take over options digits when both are defined"
        );

        // with field and data
        const field = {
            type: "monetary",
            currency_field: "c_x",
        };
        let data = {
            c_x: { res_id: 11 },
            c_y: { res_id: 12 },
        };
        assert.strictEqual(formatMonetary(200, { field, currencyId: 10, data }), "200.00 €");
        assert.strictEqual(formatMonetary(200, { field, data }), "$ 200.00");
        assert.strictEqual(formatMonetary(200, { field, currencyField: "c_y", data }), "200.00 &");

        const floatField = { type: "float" };
        data = {
            currency_id: { res_id: 11 },
        };
        assert.strictEqual(formatMonetary(200, { field: floatField, data }), "$ 200.00");
    });

    QUnit.test("formatMonetary without currency", function (assert) {
        patchWithCleanup(session, {
            currencies: {},
        });
        assert.deepEqual(
            formatMonetary(1234567.654, { currencyId: 10, humanReadable: true }),
            "1.23M"
        );
        assert.deepEqual(formatMonetary(1234567.654, { currencyId: 10 }), "1,234,567.65");
    });

    QUnit.test("formatPercentage", function (assert) {
        assert.strictEqual(formatPercentage(false), "0%");
        assert.strictEqual(formatPercentage(0), "0%");
        assert.strictEqual(formatPercentage(0.5), "50%");

        assert.strictEqual(formatPercentage(1), "100%");

        assert.strictEqual(formatPercentage(-0.2), "-20%");
        assert.strictEqual(formatPercentage(2.5), "250%");

        assert.strictEqual(formatPercentage(0.125), "12.5%");
        assert.strictEqual(formatPercentage(0.666666), "66.67%");
        assert.strictEqual(formatPercentage(125), "12500%");

        assert.strictEqual(formatPercentage(50, { humanReadable: true }), "5k%");
        assert.strictEqual(formatPercentage(0.5, { noSymbol: true }), "50");

        patchWithCleanup(localization, { grouping: [3, 0], decimalPoint: ",", thousandsSep: "." });
        assert.strictEqual(formatPercentage(0.125), "12,5%");
        assert.strictEqual(formatPercentage(0.666666), "66,67%");
    });
});
