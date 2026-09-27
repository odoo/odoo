import { animationFrame, waitFor } from "@odoo/hoot-dom";
import { advanceTime } from "@odoo/hoot-mock";
import { expect } from "@odoo/hoot";
import { MockServer, mountWithCleanup, onRpc, contains } from "@web/../tests/web_test_helpers";
import { registry } from "@web/core/registry";
import { PaymentPage } from "@pos_self_order/app/pages/payment_page/payment_page";
import { setupSelfPosEnv, getFilledSelfOrder } from "@pos_self_order/../tests/unit/utils";
import { mockBancontactCall } from "@pos_bancontact_pay/../tests/unit/ui_utils";

export const DISPLAY = "Bancontact Display";

function mockCreateBancontactPayment() {
    onRpc("/pos-self-order/create-bancontact-pay-payment", async (request) => {
        const { params } = await request.json();
        return MockServer.env["pos.payment.method"].create_bancontact_payment(
            params.payment_method_id,
            { uuid: params.line_uuid }
        );
    });
}

export async function setupKioskPaymentPage(mockOptions = {}) {
    const store = await setupSelfPosEnv("kiosk");

    // `point_of_sale`'s confirmation dialog uses the `pos` service, which
    // `setupSelfPosEnv` removes. That file is not loaded by a real kiosk, so the
    // service only has to exist for the dialog to mount here.
    registry.category("services").add("pos", { start: () => ({}) });

    await getFilledSelfOrder(store);

    mockBancontactCall(mockOptions);
    mockCreateBancontactPayment();
    onRpc(`/kiosk/payment/${store.config.id}/kiosk`, () => {
        expect.step("kiosk payment");
        return true;
    });

    await mountWithCleanup(PaymentPage, {});
    return store;
}

export async function clickBancontactMethod() {
    await clickBtn(DISPLAY);
}

export async function mockCallbackBancontactPay(store, bancontactId, bancontactStatus) {
    const errors = { CANCELLED: "Payment cancelled", EXPIRED: "Payment expired" };
    await store._onFinalizeKioskPayment({
        status: bancontactStatus === "SUCCEEDED" ? "success" : "fail",
        error: errors[bancontactStatus] || null,
        bancontact_id: bancontactId,
    });
    await animationFrame();
    await animationFrame();
}

export async function isProcessingPayment() {
    await waitFor(".payment-state-container h1:contains('Processing your payment...')");
}

export async function waitForQrCode() {
    await advanceTime(500);
    await waitFor(".payment-state-container .o_bancontact_frame");
}

export function isQrCodeShown() {
    return Boolean(document.querySelector(".payment-state-container .o_bancontact_frame"));
}

export function lastPaymentline(store) {
    return store.currentOrder.payment_ids.at(-1);
}

export async function clickBtn(buttonName) {
    await contains(`.btn:contains('${buttonName}')`).click();
    await animationFrame();
}
