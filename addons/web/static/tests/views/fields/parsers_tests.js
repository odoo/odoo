/** @odoo-module **/

import { localization } from "@web/core/l10n/localization";
import {
    parseFloat,
    parseFloatTime,
    parseInteger,
    parsePercentage,
    parseMonetary,
} from "@web/views/fields/parsers";
import { session } from "@web/session";
import { defaultLocalization } from "@web/../tests/helpers/mock_services";
import { patchWithCleanup } from "@web/../tests/helpers/utils";

function expectInvalidNumberError(assert, func, value, options) {
    let message = `${func.name} fails on value: "${value}"`;
    if (options) {
        message += ` with options: ${JSON.stringify(options)}`;
    }
    assert.throws(() => func(value, options), message);
}

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
        patchWithCleanup(localization, defaultLocalization);
    });

    QUnit.module("Parsers");

    QUnit.test("parseFloat", async (assert) => {
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

        patchWithCleanup(localization, { decimalPoint: ",", thousandsSep: false });
        assert.strictEqual(parseFloat("1234,567"), 1234.567);
    });

    QUnit.test("parseFloatTime", function (assert) {
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
        expectInvalidNumberError(assert, parseInteger, "1.234,567");
        // fallback to en localization
        assert.strictEqual(parseInteger("1,000,000"), 1000000);

        patchWithCleanup(localization, { decimalPoint: ",", thousandsSep: false });
        assert.strictEqual(parseInteger("1000000"), 1000000);
    });

    QUnit.test("parsePercentage", function (assert) {
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

    QUnit.test("parseMonetary", function (assert) {
        patchWithCleanup(session, {
            currencies: {
                1: {
                    digits: [69, 2],
                    position: "after",
                    symbol: "€",
                },
                3: {
                    digits: [69, 2],
                    position: "before",
                    symbol: "$",
                },
            },
        });

        assert.strictEqual(parseMonetary(""), 0);
        assert.strictEqual(parseMonetary("0"), 0);
        assert.strictEqual(parseMonetary("100.00\u00a0€"), 100);
        assert.strictEqual(parseMonetary("-100.00"), -100);
        assert.strictEqual(parseMonetary("1,000.00"), 1000);
        assert.strictEqual(parseMonetary("1,000,000.00"), 1000000);
        assert.strictEqual(parseMonetary("$\u00a0125.00", { currencyId: 3 }), 125);
        assert.strictEqual(parseMonetary("1,000.00\u00a0€", { currencyId: 1 }), 1000);

        assert.throws(() => parseMonetary("\u00a0", { currencyId: 3 }));
        assert.throws(() => parseMonetary("1\u00a0", { currencyId: 3 }));
        assert.throws(() => parseMonetary("\u00a01", { currencyId: 3 }));

        assert.throws(() => parseMonetary("12.00 €"));
        assert.throws(() => parseMonetary("$ 12.00", { currencyId: 3 }));
        assert.throws(() => parseMonetary("1\u00a0$", { currencyId: 1 }));
        assert.throws(() => parseMonetary("$\u00a01")); // "€" is the default currency here

        assert.throws(() => parseMonetary("1$\u00a01", { currencyId: 1 }));
        assert.throws(() => parseMonetary("$\u00a012.00\u00a034", { currencyId: 3 }));
    });

    QUnit.test("parsers fallback on english localisation", function (assert) {
        patchWithCleanup(localization, {
            decimalPoint: ",",
            thousandsSep: ".",
        });

        assert.strictEqual(parseInteger("1,000,000"), 1000000);
        assert.strictEqual(parseFloat("1,000,000.50"), 1000000.5);
    });
});
