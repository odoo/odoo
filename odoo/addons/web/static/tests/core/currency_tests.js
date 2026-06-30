/** @odoo-module **/

import { defaultLocalization } from "@web/../tests/helpers/mock_services";
import { patchWithCleanup } from "@web/../tests/helpers/utils";
import { localization } from "@web/core/l10n/localization";

import { currencies, formatCurrency } from "@web/core/currency";
import { session } from "@web/session";

QUnit.module("utils", (hooks) => {
    hooks.beforeEach(() => {
        patchWithCleanup(localization, { ...defaultLocalization, grouping: [3, 0] });
    });

    QUnit.module("Currency");

    QUnit.test("formatCurrency", function (assert) {
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

        assert.strictEqual(formatCurrency(200), "200.00");

        assert.deepEqual(formatCurrency(1234567.654, 10), "1,234,567.65\u00a0€");
        assert.deepEqual(formatCurrency(1234567.654, 11), "$\u00a01,234,567.65");
        assert.deepEqual(formatCurrency(1234567.654, 44), "1,234,567.65");
        assert.deepEqual(
            formatCurrency(1234567.654, 10, { noSymbol: true }),
            "1,234,567.65"
        );
        assert.deepEqual(
            formatCurrency(8.0, 10, { humanReadable: true }),
            "8.00\u00a0€"
        );
        assert.deepEqual(
            formatCurrency(1234567.654, 10, { humanReadable: true }),
            "1.23M\u00a0€"
        );
        assert.deepEqual(
            formatCurrency(1990000.001, 10, { humanReadable: true }),
            "1.99M\u00a0€"
        );
        assert.deepEqual(
            formatCurrency(1234567.654, 44, { digits: [69, 1] }),
            "1,234,567.7"
        );
        assert.deepEqual(
            formatCurrency(1234567.654, 11, { digits: [69, 1] }),
            "$\u00a01,234,567.7",
            "options digits should take over currency digits when both are defined"
        );
    });

    QUnit.test("formatCurrency without currency", function (assert) {
        patchWithCleanup(session, {
            currencies: {},
        });
        assert.deepEqual(
            formatCurrency(1234567.654, 10, { humanReadable: true }),
            "1.23M"
        );
        assert.deepEqual(formatCurrency(1234567.654, 10), "1,234,567.65");
    });
});
