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
import { nbsp } from "@web/core/utils/strings";

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

        // Can evaluate expression from locale with decimal point different from ".".
        assert.strictEqual(parseFloat("=1.000,1 + 2.000,2"), 3000.3);
        assert.strictEqual(parseFloat("=1.000,00 + 11.121,00"), 12121);
        assert.strictEqual(parseFloat("=1000,00 + 11122,00"), 12122);
        assert.strictEqual(parseFloat("=1000 + 11123"), 12123);

        patchWithCleanup(localization, { decimalPoint: ",", thousandsSep: false });
        assert.strictEqual(parseFloat("1234,567"), 1234.567);

        patchWithCleanup(localization, { decimalPoint: ",", thousandsSep: nbsp });
        assert.strictEqual(parseFloat("9 876,543"), 9876.543);
        assert.strictEqual(parseFloat("1  234 567,89"), 1234567.89);
        assert.strictEqual(parseFloat(`98${nbsp}765 432,1`), 98765432.1);
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
        assert.strictEqual(parseInteger("-2,147,483,648"), -2147483648);
        assert.strictEqual(parseInteger("2,147,483,647"), 2147483647);
        expectInvalidNumberError(assert, parseInteger, "1.000.000");
        expectInvalidNumberError(assert, parseInteger, "1,234.567");
        expectInvalidNumberError(assert, parseInteger, "-2,147,483,649");
        expectInvalidNumberError(assert, parseInteger, "2,147,483,648");

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
        assert.strictEqual(parseMonetary(".1"), 0.1);
        assert.strictEqual(parseMonetary("1,000,000.00"), 1000000);
        assert.strictEqual(parseMonetary("$\u00a0125.00"), 125);
        assert.strictEqual(parseMonetary("1,000.00\u00a0€"), 1000);

        assert.strictEqual(parseMonetary("\u00a0"), 0);
        assert.strictEqual(parseMonetary("1\u00a0"), 1);
        assert.strictEqual(parseMonetary("\u00a01"), 1);

        assert.strictEqual(parseMonetary("12.00 €"), 12);
        assert.strictEqual(parseMonetary("$ 12.00"), 12);
        assert.strictEqual(parseMonetary("1\u00a0$"), 1);
        assert.strictEqual(parseMonetary("$\u00a01"), 1);

        assert.throws(() => parseMonetary("1$\u00a01"));
        assert.throws(() => parseMonetary("$\u00a012.00\u00a034"));

        // nbsp as thousands separator
        patchWithCleanup(localization, { thousandsSep: "\u00a0", decimalPoint: "," });
        assert.strictEqual(parseMonetary("1\u00a0000,06\u00a0€"), 1000.06);
        assert.strictEqual(parseMonetary("$\u00a01\u00a0000,07"), 1000.07);
        assert.strictEqual(parseMonetary("1000000,08"), 1000000.08);
        assert.strictEqual(parseMonetary("$ -1\u00a0000,09"), -1000.09);

        // symbol not separated from the value
        assert.strictEqual(parseMonetary("1\u00a0000,08€"), 1000.08);
        assert.strictEqual(parseMonetary("€1\u00a0000,09"), 1000.09);
        assert.strictEqual(parseMonetary("$1\u00a0000,10"), 1000.1);
        assert.strictEqual(parseMonetary("$-1\u00a0000,11"), -1000.11);

        // any symbol
        assert.strictEqual(parseMonetary("1\u00a0000,11EUROS"), 1000.11);
        assert.strictEqual(parseMonetary("EUR1\u00a0000,12"), 1000.12);
        assert.strictEqual(parseMonetary("DOL1\u00a0000,13"), 1000.13);
        assert.strictEqual(parseMonetary("1\u00a0000,14DOLLARS"), 1000.14);
        assert.strictEqual(parseMonetary("DOLLARS+1\u00a0000,15"), 1000.15);
        assert.strictEqual(parseMonetary("EURO-1\u00a0000,16DOGE"), -1000.16);

        // comma as decimal point and dot as thousands separator
        patchWithCleanup(localization, { thousandsSep: ".", decimalPoint: "," });
        assert.strictEqual(parseMonetary("10,08"), 10.08);
        assert.strictEqual(parseMonetary(""), 0);
        assert.strictEqual(parseMonetary("0"), 0);
        assert.strictEqual(parseMonetary("100,12\u00a0€"), 100.12);
        assert.strictEqual(parseMonetary("-100,12"), -100.12);
        assert.strictEqual(parseMonetary("1.000,12"), 1000.12);
        assert.strictEqual(parseMonetary(",1"), 0.1);
        assert.strictEqual(parseMonetary("1.000.000,12"), 1000000.12);
        assert.strictEqual(parseMonetary("$\u00a0125,12"), 125.12);
        assert.strictEqual(parseMonetary("1.000,00\u00a0€"), 1000);
        assert.strictEqual(parseMonetary(","), 0);
        assert.strictEqual(parseMonetary("1\u00a0"), 1);
        assert.strictEqual(parseMonetary("\u00a01"), 1);
        assert.strictEqual(parseMonetary("12,34 €"), 12.34);
        assert.strictEqual(parseMonetary("$ 12,34"), 12.34);

        // Can evaluate expression
        assert.strictEqual(parseMonetary("=1.000,1 + 2.000,2"), 3000.3);
        assert.strictEqual(parseMonetary("=1.000,00 + 11.121,00"), 12121);
        assert.strictEqual(parseMonetary("=1000,00 + 11122,00"), 12122);
        assert.strictEqual(parseMonetary("=1000 + 11123"), 12123);
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
