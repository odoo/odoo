import { expect, test } from "@odoo/hoot";
import { FeedbackScreen } from "@point_of_sale/app/screens/feedback_screen/feedback_screen";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { definePosModels } from "../data/generate_model_definitions";
import { getFilledOrder, setupPosEnv } from "../utils";

definePosModels();

test("Total on receipt always incl", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    order.config.iface_tax_included = "total";
    await mountWithCleanup(FeedbackScreen, {
        props: { orderUuid: order.uuid },
    });
    expect(".feedback-screen .amount-container .amount:only").toHaveText("$595.00");
});

test("Total on receipt always incl with tax excluded", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    order.config.iface_tax_included = "subtotal";
    await mountWithCleanup(FeedbackScreen, {
        props: { orderUuid: order.uuid },
    });
    expect(".feedback-screen .amount-container .amount:only").toHaveText("$595.00");
});

test("Feedback total uses converted order amount, not payment amount", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const eur = store.models["res.currency"].get(125);
    const payment = order.addPaymentline(store.config.payment_method_ids[0], {
        currency: eur,
    }).data;
    payment.setAmount(3000, eur);

    await mountWithCleanup(FeedbackScreen, {
        props: { orderUuid: order.uuid },
    });

    const expectedAmount = store
        .formatCurrency(
            eur.convert(order.currency.convertToDefaultCurrency(order.totalDue)),
            eur.id
        )
        .replace(/\u00a0/g, "");
    expect(".feedback-screen .amount-container .amount:only").toHaveText(expectedAmount);
    expect(payment.getAmount()).toBeGreaterThan(order.totalDue);
});

test("canEditPayment", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    // edit
    order.state = "paid";
    store.config.iface_print_auto = true;
    expect(store.canEditPayment(order)).toBe(false);
    store.config.iface_print_auto = false;
    expect(store.canEditPayment(order)).toBe(true);
    order.nb_print = 1;
    expect(store.canEditPayment(order)).toBe(false);
});
