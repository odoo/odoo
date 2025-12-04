import { test, expect } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { setupPosEnv, getFilledOrder } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { FeedbackScreen } from "@point_of_sale/app/screens/feedback_screen/feedback_screen";

definePosModels();

test("canEditPayment", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const feedbackScreen = await mountWithCleanup(FeedbackScreen, {
        props: { orderUuid: order.uuid },
    });
    const admin = store.models["hr.employee"].get(2);
    store.setCashier(admin);
    expect(feedbackScreen.canEditPayment).toBe(true);
    const emp = store.models["hr.employee"].get(3);
    store.setCashier(emp);
    expect(feedbackScreen.canEditPayment).toBe(false);
});
