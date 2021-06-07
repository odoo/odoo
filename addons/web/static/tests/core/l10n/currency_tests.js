/** @odoo-module **/

import { formatCurrency, parseCurrency } from "@web/core/l10n/currency";
import { localization } from "@web/core/l10n/localization";
import { patch, unpatch } from "@web/core/utils/patch";
import { defaultLocalization } from "../../helpers/mock_services";
import { patchWithCleanup } from "@web/../tests/helpers/utils";

QUnit.module("utils", (hooks) => {
    hooks.beforeEach(() => {
        patchWithCleanup(localization, defaultLocalization);
    });
    QUnit.module("Currency");

    QUnit.test("format", async (assert) => {
        assert.deepEqual(formatCurrency(1234567.654, 1), "$ 1,234,567.65");
        assert.deepEqual(formatCurrency(1234567.654, 2), "1,234,567.65 €");
        assert.deepEqual(
            formatCurrency(1234567.654, 44),
            "1,234,567.65",
            "undefined currency should be fine too"
        );
        assert.deepEqual(formatCurrency(1234567.654, 2, { noSymbol: true }), "1,234,567.65");
        assert.deepEqual(formatCurrency(1234567.654, 2, { humanReadable: true }), "1M €");
        assert.deepEqual(formatCurrency(1234567.654, 44, { digits: [69, 1] }), "1,234,567.7");
        assert.deepEqual(
            formatCurrency(1234567.654, 1, { digits: [69, 1] }),
            "$ 1,234,567.65",
            "currency digits should take over options digits when both are defined"
        );
        assert.strictEqual(formatCurrency(false, 2), "");
    });

    QUnit.test("parseCurrency", function (assert) {
        assert.expect(17);

        patchWithCleanup(odoo.session_info, {
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

        assert.strictEqual(parseCurrency(""), 0);
        assert.strictEqual(parseCurrency("0"), 0);
        assert.strictEqual(parseCurrency("100.00&nbsp;€"), 100);
        assert.strictEqual(parseCurrency("-100.00"), -100);
        assert.strictEqual(parseCurrency("1,000.00"), 1000);
        assert.strictEqual(parseCurrency("1,000,000.00"), 1000000);
        assert.strictEqual(parseCurrency("$&nbsp;125.00", { currencyId: 3 }), 125);
        assert.strictEqual(parseCurrency("1,000.00&nbsp;€", { currencyId: 1 }), 1000);

        assert.throws(() => parseCurrency("&nbsp;", { currencyId: 3 }));
        assert.throws(() => parseCurrency("1&nbsp;", { currencyId: 3 }));
        assert.throws(() => parseCurrency("&nbsp;1", { currencyId: 3 }));

        assert.throws(() => parseCurrency("12.00 €"));
        assert.throws(() => parseCurrency("$ 12.00", { currencyId: 3 }));
        assert.throws(() => parseCurrency("1&nbsp;$", { currencyId: 1 }));
        assert.throws(() => parseCurrency("$&nbsp;1")); // "€" is the default currency here

        assert.throws(() => parseCurrency("1$&nbsp;1", { currencyId: 1 }));
        assert.throws(() => parseCurrency("$&nbsp;12.00&nbsp;34", { currencyId: 3 }));
    });

    // BOI: we do not have a parse method, but here are some tests if we want to add this at some point.
    // QUnit.test("parse", async (assert) => {
    //   serviceRegistry = new Registry();
    //   serviceRegistry.add("currency", currencyService);
    //   env = await makeTestEnv({ serviceRegistry });
    //   const { currency: curSvc } = env.services;
    //   assert.deepEqual(curSvc.parse("$ 1234567.65", "USD"), 1234567.65);
    //   assert.deepEqual(curSvc.parse("1234567.65 €", "EUR"), 1234567.65);
    //   assert.deepEqual(curSvc.parse("1234567.65 €", "EUR"), 1234567.65);
    //   assert.deepEqual(curSvc.parse("$ 1,234,567.65", "USD"), 1234567.65);
    //   assert.deepEqual(curSvc.parse("1,234,567.65 €", "EUR"), 1234567.65);
    //   assert.deepEqual(curSvc.parse("1,234,567.65 €", "EUR"), 1234567.65);
    //   assert.throws(function () {
    //     curSvc.parse("1234567.65 €", "OdooCoin");
    //   }, /currency not found/);
    //   assert.throws(function () {
    //     curSvc.parse("$ 1,234,567.65", "EUR");
    //   }, /not a correct 'EUR' monetary field/);
    // });
});
