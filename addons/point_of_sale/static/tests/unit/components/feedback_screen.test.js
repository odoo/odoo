import { test, expect, destroy } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { setupPosEnv, getFilledOrder } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";
import { queryOne } from "@odoo/hoot-dom";
import { FeedbackScreen } from "@point_of_sale/app/screens/feedback_screen/feedback_screen";

definePosModels();

test("Total on receipt always incl", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    order.config.iface_tax_included = "total";
    const feedbackScreen = await mountWithCleanup(FeedbackScreen, {
        props: { orderUuid: order.uuid },
    });
    let total = queryOne(".feedback-screen .amount-container .amount");
    expect(total).toHaveText("17.85");
    destroy(feedbackScreen);

    // create new feedback screen with tax excluded
    order.config.iface_tax_included = "subtotal";
    await mountWithCleanup(FeedbackScreen, {
        props: { orderUuid: order.uuid },
    });
    total = queryOne(".feedback-screen .amount-container .amount");
    expect(total).toHaveText("17.85");
});

test("canEditPayment", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const feedbackScreen = await mountWithCleanup(FeedbackScreen, {
        props: { orderUuid: order.uuid },
    });
    store.config.iface_print_auto = true;
    expect(feedbackScreen.canEditPayment).toBe(false);
    store.config.iface_print_auto = false;
    expect(feedbackScreen.canEditPayment).toBe(true);
    order.nb_print = 1;
    expect(feedbackScreen.canEditPayment).toBe(false);
});
