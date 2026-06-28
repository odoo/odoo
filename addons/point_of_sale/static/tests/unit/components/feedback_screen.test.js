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
    expect(".feedback-screen .amount-container .amount:only").toHaveText("$17.85");
});

test("Total on receipt always incl with tax excluded", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    order.config.iface_tax_included = "subtotal";
    await mountWithCleanup(FeedbackScreen, {
        props: { orderUuid: order.uuid },
    });
    expect(".feedback-screen .amount-container .amount:only").toHaveText("$17.85");
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
