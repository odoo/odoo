import { test, expect } from "@odoo/hoot";
import { mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { PaymentPage } from "@pos_self_order/app/pages/payment_page/payment_page";
import { setupSelfPosEnv, getFilledSelfOrder } from "@pos_self_order/../tests/unit/utils";
import { definePosSelfModels } from "@pos_self_order/../tests/unit/data/generate_model_definitions";

definePosSelfModels();

const setupPaymentPage = async (mode = "kiosk", serviceMode = "counter", payAfter = "each") => {
    const store = await setupSelfPosEnv(mode, serviceMode, payAfter);
    await getFilledSelfOrder(store);
    const paymentPage = await mountWithCleanup(PaymentPage, {});

    return { store, paymentPage };
};

test("test_online_payment_kiosk_qr_code: shows QR code for kiosk online payment", async () => {
    const { paymentPage } = await setupPaymentPage("kiosk");

    paymentPage.state.paymentMethodId = 99;

    expect(paymentPage.selectedPaymentIsOnline).toBe(true);
    expect(paymentPage.showQrCode).toBe(true);
});

test("test_online_payment_kiosk_qr_code: generates QR code from the online payment URL", async () => {
    const { paymentPage, store } = await setupPaymentPage("kiosk");
    paymentPage.state.paymentMethodId = 99;

    patchWithCleanup(store, {
        async sendDraftOrderToServer() {
            return {
                id: 42,
                access_token: "order-token",
                config_id: { id: store.config.id },
                state: "draft",
            };
        },
        getOnlinePaymentUrl() {
            return "https://example.com/pay/42";
        },
    });

    let generatedUrl = null;
    patchWithCleanup(paymentPage, {
        generateQrcodeImg(url) {
            generatedUrl = url;
        },
    });

    await paymentPage.startPayment();

    expect(generatedUrl).toBe("https://example.com/pay/42");
});

test("test_kiosk_cart_restore_and_cancel: back clears pending line changes before returning to cart", async () => {
    const { paymentPage, store } = await setupPaymentPage("kiosk");
    const back = [];

    patchWithCleanup(store.router, {
        back() {
            back.push(true);
        },
    });

    store.currentOrder.uiState.lineChanges = { foo: true };
    paymentPage.back();

    expect(store.currentOrder.uiState.lineChanges).toEqual({});
    expect(back).toHaveLength(1);
});
