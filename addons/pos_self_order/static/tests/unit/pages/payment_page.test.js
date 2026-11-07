import { test, expect } from "@odoo/hoot";
import { mountWithCleanup, onRpc } from "@web/../tests/web_test_helpers";
import { PaymentPage } from "@pos_self_order/app/pages/payment_page/payment_page";
import { setupSelfPosEnv, getFilledSelfOrder } from "../utils";
import { definePosSelfModels } from "../data/generate_model_definitions";

definePosSelfModels();

test("startPayment sends the signed partner of the order to the backend", async () => {
    const store = await setupSelfPosEnv();
    await getFilledSelfOrder(store);
    const signedPartnerId = "7-0123456789abcdef";
    const connectedData = store.models.connectNewData({
        "res.partner": [{ id: signedPartnerId, name: "Demo User" }],
    });
    store.currentOrder.partner_id = connectedData["res.partner"][0];

    let sentOrder;
    onRpc("/kiosk/payment/1/kiosk", async (request) => {
        const { params } = await request.json();
        sentOrder = params.order;
        return true;
    });
    const paymentPage = await mountWithCleanup(PaymentPage, {});
    await paymentPage.startPayment();

    expect(store.paymentError).toBe(false);
    expect(sentOrder.partner_id).toBe(signedPartnerId);
});
