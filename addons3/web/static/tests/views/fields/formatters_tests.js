/** @odoo-module **/

import { markup } from "@odoo/owl";
import { defaultLocalization } from "@web/../tests/helpers/mock_services";
import { patchWithCleanup } from "@web/../tests/helpers/utils";
import { currencies } from "@web/core/currency";
import { localization } from "@web/core/l10n/localization";
import {
    formatFloat,
    formatFloatFactor,
    formatFloatTime,
    formatJson,
    formatInteger,
    formatMany2one,
    formatMonetary,
    formatPercentage,
    formatReference,
    formatText,
    formatX2many,
} from "@web/views/fields/formatters";

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
        patchWithCleanup(localization, { ...defaultLocalization, grouping: [3, 0] });
    });

    QUnit.module("Formatters");

    QUnit.test("formatFloat", function (assert) {
        assert.strictEqual(formatFloat(false), "");
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
        assert.strictEqual(formatFloatTime(0.58), "00:35");
        assert.strictEqual(formatFloatTime(2 / 60, { displaySeconds: true }), "00:02:00");
        assert.strictEqual(
            formatFloatTime(2 / 60 + 1 / 3600, { displaySeconds: true }),
            "00:02:01"
        );
        assert.strictEqual(
            formatFloatTime(2 / 60 + 2 / 3600, { displaySeconds: true }),
            "00:02:02"
        );
        assert.strictEqual(
            formatFloatTime(2 / 60 + 3 / 3600, { displaySeconds: true }),
            "00:02:03"
        );
        assert.strictEqual(formatFloatTime(0.25, { displaySeconds: true }), "00:15:00");
        assert.strictEqual(formatFloatTime(0.25 + 15 / 3600, { displaySeconds: true }), "00:15:15");
        assert.strictEqual(formatFloatTime(0.25 + 45 / 3600, { displaySeconds: true }), "00:15:45");
        assert.strictEqual(formatFloatTime(56 / 3600, { displaySeconds: true }), "00:00:56");
        assert.strictEqual(formatFloatTime(-0.5), "-00:30");

        const options = { noLeadingZeroHour: true };
        assert.strictEqual(formatFloatTime(2, options), "2:00");
        assert.strictEqual(formatFloatTime(3.5, options), "3:30");
        assert.strictEqual(formatFloatTime(3.5, { ...options, displaySeconds: true }), "3:30:00");
        assert.strictEqual(
            formatFloatTime(3.5 + 15 / 3600, { ...options, displaySeconds: true }),
            "3:30:15"
        );
        assert.strictEqual(
            formatFloatTime(3.5 + 45 / 3600, { ...options, displaySeconds: true }),
            "3:30:45"
        );
        assert.strictEqual(
            formatFloatTime(56 / 3600, { ...options, displaySeconds: true }),
            "0:00:56"
        );
        assert.strictEqual(formatFloatTime(-0.5, options), "-0:30");
    });

    QUnit.test("formatJson", function (assert) {
        assert.strictEqual(formatJson(false), "");
        assert.strictEqual(formatJson({}), "{}");
        assert.strictEqual(formatJson({ 1: 111 }), '{"1":111}');
        assert.strictEqual(formatJson({ 9: 11, 666: 42 }), '{"9":11,"666":42}');
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
        assert.strictEqual(formatMany2one(false), "");
        assert.strictEqual(formatMany2one([false, "M2O value"]), "M2O value");
        assert.strictEqual(formatMany2one([1, false]), "Unnamed");
        assert.strictEqual(formatMany2one([1, "M2O value"]), "M2O value");
        assert.strictEqual(formatMany2one([1, "M2O value"], { escape: true }), "M2O%20value");
    });

    QUnit.test("formatText", function (assert) {
        assert.strictEqual(formatText(false), "");
        assert.strictEqual(formatText("value"), "value");
        assert.strictEqual(formatText(1), "1");
        assert.strictEqual(formatText(1.5), "1.5");
        assert.strictEqual(formatText(markup("<p>This is a Test</p>")), "<p>This is a Test</p>");
        assert.strictEqual(formatText([1, 2, 3, 4, 5]), "1,2,3,4,5");
        assert.strictEqual(formatText({ a: 1, b: 2 }), "[object Object]");
    });

    QUnit.test("formatX2many", function (assert) {
        // Results are cast as strings since they're lazy translated.
        assert.strictEqual(String(formatX2many({ currentIds: [] })), "No records");
        assert.strictEqual(String(formatX2many({ currentIds: [1] })), "1 record");
        assert.strictEqual(String(formatX2many({ currentIds: [1, 3] })), "2 records");
    });

    QUnit.test("formatMonetary", function (assert) {
        patchWithCleanup(currencies, {
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

        const field = {
            type: "monetary",
            currency_field: "c_x",
        };
        let data = {
            c_x: [11],
            c_y: 12,
        };
        assert.deepEqual(formatMonetary(200, { field, currencyId: 10, data }), "200.00\u00a0€");
        assert.deepEqual(formatMonetary(200, { field, data }), "$\u00a0200.00");
        assert.deepEqual(formatMonetary(200, { field, currencyField: "c_y", data }), "200.00\u00a0&");

        const floatField = { type: "float" };
        data = {
            currency_id: [11],
        };
        assert.deepEqual(formatMonetary(200, { field: floatField, data }), "$\u00a0200.00");
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

    QUnit.test("formatReference", function (assert) {
        assert.strictEqual(formatReference(false), "");
        const value = { resModel: "product", resId: 2, displayName: "Chair" };
        assert.strictEqual(formatReference(value), "Chair");
    });
});
