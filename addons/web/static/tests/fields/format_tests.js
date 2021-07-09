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
} from "@web/fields/format";
import { defaultLocalization } from "../helpers/mock_services";
import { patchWithCleanup } from "../helpers/utils";

QUnit.module("Format Fields", (hooks) => {
    hooks.beforeEach(() => {
        patchWithCleanup(localization, defaultLocalization);
    });

    QUnit.test("formatFloat", function (assert) {
        patchWithCleanup(localization, { grouping: [3, 3, 3, 3] });
        assert.strictEqual(formatFloat(1000000), "1,000,000.00");

        patchWithCleanup(localization, { grouping: [3, 2, -1] });
        assert.strictEqual(formatFloat(106500), "1,06,500.00");

        patchWithCleanup(localization, { grouping: [1, 2, -1] });
        assert.strictEqual(formatFloat(106500), "106,50,0.00");

        patchWithCleanup(localization, {
            grouping: [3, 0],
            decimalPoint: ",",
            thousandsSep: ".",
        });
        assert.strictEqual(formatFloat(6000), "6.000,00");
        assert.strictEqual(formatFloat(false), "");
    });

    QUnit.test("formatFloatFactor", function (assert) {
        assert.strictEqual(formatFloatFactor(false), "");
        assert.strictEqual(formatFloatFactor(6000), "6,000.00");
        assert.strictEqual(formatFloatFactor(6000, null, { factor: 3 }), "18,000.00");
        assert.strictEqual(formatFloatFactor(6000, null, { factor: 0.5 }), "3,000.00");
    });

    QUnit.test("formatFloatTime", function (assert) {
        assert.strictEqual(formatFloatTime(2), "02:00");
        assert.strictEqual(formatFloatTime(3.5), "03:30");
        assert.strictEqual(formatFloatTime(0.25), "00:15");

        assert.strictEqual(formatFloatTime(-0.5), "-00:30");

        const options = { noLeadingZeroHour: true };
        assert.strictEqual(formatFloatTime(2, null, options), "2:00");
        assert.strictEqual(formatFloatTime(3.5, null, options), "3:30");
        assert.strictEqual(formatFloatTime(-0.5, null, options), "-0:30");
    });

    QUnit.test("formatInteger", function (assert) {
        patchWithCleanup(localization, { grouping: [3, 3, 3, 3] });
        assert.strictEqual(formatInteger(1000000), "1,000,000");

        patchWithCleanup(localization, { grouping: [3, 2, -1] });
        assert.strictEqual(formatInteger(106500), "1,06,500");

        patchWithCleanup(localization, { grouping: [1, 2, -1] });
        assert.strictEqual(formatInteger(106500), "106,50,0");

        assert.strictEqual(formatInteger(0), "0");
        assert.strictEqual(formatInteger(false), "");
    });

    QUnit.test("formatMany2one", function (assert) {
        assert.strictEqual(formatMany2one(null), "");
        assert.strictEqual(formatMany2one([1, "A M2O value"]), "A M2O value");
        assert.strictEqual(
            formatMany2one({
                data: { display_name: "A M2O value" },
            }),
            "A M2O value"
        );

        assert.strictEqual(
            formatMany2one([1, "A M2O value"], null, { escape: true }),
            "A%20M2O%20value"
        );
        assert.strictEqual(
            formatMany2one(
                {
                    data: { display_name: "A M2O value" },
                },
                null,
                { escape: true }
            ),
            "A%20M2O%20value"
        );
    });

    QUnit.test("formatMonetary", function (assert) {
        const field = {
            type: "monetary",
            currency_field: "c_x",
        };
        let data = {
            c_x: { res_id: 11 },
            c_y: { res_id: 12 },
        };
        patchWithCleanup(odoo.session_info.currencies, {
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

        assert.strictEqual(formatMonetary(200, field, { currencyId: 10, data }), "200.00 €");
        assert.strictEqual(formatMonetary(200, field, { data }), "$ 200.00");
        assert.strictEqual(formatMonetary(200, field, { currencyField: "c_y", data }), "200.00 &");

        const floatField = { type: "float" };
        data = {
            currency_id: { res_id: 11 },
        };
        assert.strictEqual(formatMonetary(200, floatField, { data }), "$ 200.00");
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

        const options = {
            humanReadable: () => true,
        };
        assert.strictEqual(formatPercentage(50, null, options), "5k%");
        assert.strictEqual(formatPercentage(0.5, null, { noSymbol: true }), "50");

        patchWithCleanup(localization, { grouping: [3, 0], decimalPoint: ",", thousandsSep: "." });
        assert.strictEqual(formatPercentage(0.125), "12,5%");
        assert.strictEqual(formatPercentage(0.666666), "66,67%");
    });
});
