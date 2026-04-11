/** @odoo-module */

import { Orderline, Order } from "@point_of_sale/app/store/models";

QUnit.module("unit tests for models", () => {
    QUnit.test("Orderline.get_all_prices: locked uses stored subtotals, unlocked recomputes", function (assert) {
            // Locked line: returns stored subtotals, scales by qty ratio,
            // reconstructs pre-discount values, and preserves sign for refunds.
            // Unlocked line: falls through to the recompute path.
            const locked = Object.create(Orderline.prototype);
            locked.quantity = 2;
            locked.discount = 50;
            locked.price_subtotal = 30.0;       // 30 * 2 * 0.5
            locked.price_subtotal_incl = 34.5;  // 34.5 * 2 * 0.5
            locked.order = { locked: true };

            assert.strictEqual(locked.get_price_with_tax(), 34.5);
            assert.strictEqual(locked.get_price_without_tax(), 30.0);

            const unit = locked.get_all_prices(1);
            assert.strictEqual(unit.priceWithTax, 17.25);
            assert.strictEqual(unit.priceWithoutTax, 15.0);
            assert.strictEqual(unit.priceWithoutTaxBeforeDiscount, 30.0);
            assert.strictEqual(unit.priceWithTaxBeforeDiscount, 34.5);

            // Unlocked line: price_subtotal/price_subtotal_incl are not pinned,
            // so get_all_prices must recompute from current taxes.
            const unlocked = Object.create(Orderline.prototype);
            unlocked.price = 30;
            unlocked.discount = 0;
            unlocked.quantity = 1;
            unlocked.product = { taxes_id: [] };
            unlocked.tax_ids = undefined;
            unlocked.order = { locked: false, fiscal_position: null };
            unlocked.pos = {
                dp: { "Product Price": 2 },
                taxes_by_id: {},
                get_taxes_after_fp: () => [],
                currency: { rounding: 0.01 },
                compute_all: (taxes, price, qty) => ({
                    taxes: [],
                    total_included: price * qty,
                    total_excluded: price * qty,
                }),
            };

            const recomputed = unlocked.get_all_prices(1);
            assert.strictEqual(recomputed.priceWithTax, 30);
            assert.strictEqual(recomputed.priceWithoutTax, 30);

            // Refund line: negative quantity preserves sign through the same
            // stored-subtotals path.
            const refund = Object.create(Orderline.prototype);
            refund.quantity = -1;
            refund.price_subtotal = -30.0;
            refund.price_subtotal_incl = -34.5;

            const refundPrices = refund.get_all_prices(-1);
            assert.strictEqual(refundPrices.priceWithTax, -34.5);
            assert.strictEqual(refundPrices.priceWithoutTax, -30.0);
        }
    );

    QUnit.test("Order totals: locked uses stored amounts, unlocked recomputes", function (assert) {
            // Locked order: returns stored amount_total / amount_tax.
            // Unlocked order: ignores them and sums from the lines.
            const locked = Object.create(Order.prototype);
            locked.locked = true;
            locked.amount_total = 34.5;
            locked.amount_tax = 4.5;

            assert.strictEqual(locked.get_total_with_tax(), 34.5);
            assert.strictEqual(locked.get_total_tax(), 4.5);

            // Unlocked: amount_total/amount_tax are ignored, totals come from
            // the lines (here empty, so 0).
            const unlocked = Object.create(Order.prototype);
            unlocked.locked = false;
            unlocked.amount_total = 999;
            unlocked.amount_tax = 99;
            unlocked.orderlines = [];
            unlocked.pos = {
                currency: { rounding: 0.01 },
                company: { tax_calculation_rounding_method: "round_per_line" },
            };

            assert.strictEqual(unlocked.get_total_with_tax(), 0);
            assert.strictEqual(unlocked.get_total_tax(), 0);
        }
    );

});
