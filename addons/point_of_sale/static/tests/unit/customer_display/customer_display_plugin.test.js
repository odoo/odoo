import { test, expect } from "@odoo/hoot";
import { formatCurrency } from "@web/core/currency";
import { getFilledOrder, setupPosEnv, expectFormattedPrice } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";

definePosModels();

test("_buildDisplayPayload", async () => {
    const store = await setupPosEnv();
    const customerDisplay = store.customerDisplay;
    const order = await getFilledOrder(store);

    const payload = customerDisplay._buildDisplayPayload(order);
    const lines = payload.lines;

    expect(lines).toHaveLength(2);
    expect(payload.selectedLineUuid).toBe(lines[1].uuid);

    const prices = payload.extra_data.prices;
    expectFormattedPrice(prices.total_amount, "$ 595.00");
    expectFormattedPrice(prices.tax_amount, "$ 95.00");
    expectFormattedPrice(prices.subtotal_amount, "$ 500.00");
    expect(payload.change).toBeEmpty();
});

test("_buildDisplayPayload uses the payment currency for total and change", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const euro = store.models["res.currency"].get(125);
    const payment = order.addPaymentline(store.config.payment_method_ids[0], {
        currency: euro,
    }).data;
    payment.setAmount(800, euro);

    const payload = store.customerDisplay._buildDisplayPayload(order);
    const expectedTotal = order.orderCurrency.convertFormatted(order.totalDue);

    expectFormattedPrice(payload.paymentAmountInCurrency, expectedTotal);
    expect(payload.amountSettlements.label).toBe("Change");
    expectFormattedPrice(
        payload.amountSettlements.amount,
        formatCurrency(Math.abs(order.remainingDueAmount), euro.id)
    );
});
