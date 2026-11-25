import { describe, expect, test } from "@odoo/hoot";
import { setupPosEnv } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";
import { setProductPrice } from "../receipt_utils";

definePosModels();

/**
 * Orders mixing sale lines (positive quantity) and refund lines (negative quantity).
 * Sale product: 10.04 + 15% tax, refund product: 2.36 + 15% tax, taxes rounded globally.
 *
 * - Refund lines are rounded apart from sale lines: the sale tax 1.506 and the refund tax
 *   -0.354 are rounded separately (1.51 and -0.35), not together (1.152 -> 1.15).
 * - The order is a refund when its total is negative.
 * - The cash rounding goes the other way for a negative total (UP rounds a refund toward zero).
 *
 * The backend runs the same scenarios and compares its values with the ones of the frontend,
 * keep them in sync with test_mixed_sale_refund.py and mixed_sale_refund_tour.js.
 */
const SCENARIOS = {
    net_positive: {
        lines: [
            ["sale", 1],
            ["refund", -1],
        ],
        isRefund: false,
        total: 8.84,
        tax: 1.16,
        linesTotal: [11.55, -2.71],
        paymentCashRoundingUp: 8.85,
    },
    net_negative: {
        lines: [
            ["sale", 1],
            ["refund", -6],
        ],
        isRefund: true,
        total: -4.73,
        tax: -0.61,
        linesTotal: [11.55, -16.28],
        paymentCashRoundingUp: -4.7,
    },
    pure_refund: {
        lines: [["refund", -6]],
        isRefund: true,
        total: -16.28,
        tax: -2.12,
        linesTotal: [-16.28],
        paymentCashRoundingUp: -16.25,
    },
};

const setupMixedEnv = async () => {
    const store = await setupPosEnv();
    store.company.tax_calculation_rounding_method = "round_globally";
    const tax15 = store.models["account.tax"].get(1);
    const products = {
        sale: store.models["product.template"].get(15),
        refund: store.models["product.template"].get(16),
    };
    setProductPrice(products.sale, 10.04, [tax15]);
    setProductPrice(products.refund, 2.36, [tax15]);
    const bankPm = store.models["pos.payment.method"].find((pm) => pm.type === "bank");
    return { store, products, bankPm };
};

const createScenarioOrder = async (store, products, scenario) => {
    const order = store.addNewOrder();
    order.pricelist_id = false;
    for (const [product, qty] of scenario.lines) {
        await store.addLineToOrder({ product_tmpl_id: products[product], qty }, order);
    }
    return order;
};

const setupCashRoundingUp = (store) => {
    store.config.cash_rounding = true;
    store.config.only_round_cash_method = false;
    store.config.rounding_method = store.models["account.cash.rounding"].create({
        name: "Mixed rounding UP",
        rounding: 0.05,
        rounding_method: "UP",
        strategy: "add_invoice_line",
    });
};

describe("mixed sale and refund orders", () => {
    for (const [name, scenario] of Object.entries(SCENARIOS)) {
        test(`${name}: totals and sign`, async () => {
            const { store, products, bankPm } = await setupMixedEnv();
            const order = await createScenarioOrder(store, products, scenario);

            expect(order.isRefund).toBe(scenario.isRefund);
            expect(store.currency.round(order.priceIncl)).toBe(scenario.total);
            expect(store.currency.round(order.amountTaxes)).toBe(scenario.tax);
            expect(order.lines.map((line) => line.priceIncl)).toEqual(scenario.linesTotal);

            order.addPaymentline(bankPm);
            expect(order.payment_ids[0].amount).toBe(scenario.total);
            expect(order.remainingDue).toBe(0);
        });

        test(`${name}: cash rounding UP is inverted for a negative total`, async () => {
            const { store, products, bankPm } = await setupMixedEnv();
            setupCashRoundingUp(store);
            const order = await createScenarioOrder(store, products, scenario);

            expect(order.isRefund).toBe(scenario.isRefund);
            expect(order.totalDue).toBe(scenario.paymentCashRoundingUp);

            order.addPaymentline(bankPm);
            expect(order.payment_ids[0].amount).toBe(scenario.paymentCashRoundingUp);
            expect(order.remainingDue).toBe(0);
        });
    }

    test("refund lines are rounded apart from sale lines", async () => {
        const { store, products } = await setupMixedEnv();
        const order = await createScenarioOrder(store, products, SCENARIOS.net_positive);
        const [saleLine, refundLine] = order.prices.baseLines;

        expect(saleLine.is_refund).toBe(false);
        expect(refundLine.is_refund).toBe(true);
        // Rounded together, the tax would be round(1.506 - 0.354) = 1.15
        expect(store.currency.round(order.amountTaxes)).toBe(1.16);
    });
});
