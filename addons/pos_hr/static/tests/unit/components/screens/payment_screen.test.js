import { test, expect } from "@odoo/hoot";
import { setupPosEnv, getFilledOrder } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

test("getAvailablePaymentMethods", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const card = store.models["pos.payment.method"].get(2);
    const isAvailable = () => store.paymentMethods.getAvailablePaymentMethods(order).includes(card);

    // Cashier Resteictive
    store.accessRight.cashier._role = "restrictive";
    card.type = "pay_later";
    expect(isAvailable()).toBe(false);

    card.type = "cash";
    expect(isAvailable()).toBe(true);

    // Cashier Admin
    store.accessRight.cashier._role = "manager";
    card.type = "pay_later";
    expect(isAvailable()).toBe(true);

    card.type = "cash";
    expect(isAvailable()).toBe(true);

    // Is Refund + no payment interface
    order.is_refund = true;
    expect(isAvailable()).toBe(true);

    // Is Refund + payment interface not supporting refunds
    card.payment_interface = { supports_refunds: false };
    expect(isAvailable()).toBe(false);

    // Is Refund + payment interface supporting refunds
    card.payment_interface = { supports_refunds: true };
    expect(isAvailable()).toBe(true);
});
