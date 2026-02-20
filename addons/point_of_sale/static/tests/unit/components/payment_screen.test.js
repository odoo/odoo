import { test, expect, animationFrame } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { setupPosEnv, getFilledOrder, expectFormattedPrice } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";
import { queryOne } from "@odoo/hoot-dom";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";

definePosModels();

test("Change always incl", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const firstPm = store.models["pos.payment.method"].getFirst();
    order.config.iface_tax_included = "total";
    const comp = await mountWithCleanup(PaymentScreen, {
        props: { orderUuid: order.uuid },
    });
    await comp.addNewPaymentLine(firstPm);
    order.payment_ids[0].setAmount(20);
    await animationFrame();
    const total = queryOne(".amount");
    expectFormattedPrice(total.attributes.amount.value, "$ -2.15");
    order.config.iface_tax_included = "subtotal";
    await animationFrame();
    const subtotal = queryOne(".amount");
    expectFormattedPrice(subtotal.attributes.amount.value, "$ -2.15");
});

test("showPaymentMethod", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const card = store.models["pos.payment.method"].get(2);
    const comp = await mountWithCleanup(PaymentScreen, {
        props: { orderUuid: order.uuid },
    });

    // Cashier Minimal
    store.cashier._role = "minimal";
    card.type = "pay_later";
    expect(comp.showPaymentMethod(card)).toBe(false);

    card.type = "cash";
    expect(comp.showPaymentMethod(card)).toBe(true);

    // Cashier Admin
    store.cashier._role = "admin";
    card.type = "pay_later";
    expect(comp.showPaymentMethod(card)).toBe(true);

    card.type = "cash";
    expect(comp.showPaymentMethod(card)).toBe(true);

    // Is Refund + no payment interface
    order.is_refund = true;
    expect(comp.showPaymentMethod(card)).toBe(true);

    // Is Refund + payment interface not supporting refunds
    card.payment_interface = { supports_refunds: false };
    expect(comp.showPaymentMethod(card)).toBe(false);

    // Is Refund + payment interface supporting refunds
    card.payment_interface = { supports_refunds: true };
    expect(comp.showPaymentMethod(card)).toBe(true);
});
