import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as FeedbackScreen from "@point_of_sale/../tests/pos/tours/utils/feedback_screen_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";

import { registry } from "@web/core/registry";

function isQRDisplayedinDialog() {
    return [
        {
            content: "Verify QR image is displayed",
            trigger: ".modal-content img[src^='data:image/svg+xml;base64,']",
            run: "click",
        },
    ].flat();
}

function addProductandPay() {
    return [
        ProductScreen.addOrderline("Test Product"),
        ProductScreen.selectedOrderlineHas("Test Product"),
        ProductScreen.clickPayButton(),

        PaymentScreen.totalIs("1,000.00"),
        PaymentScreen.clickPaymentMethod("QRIS", true, { amount: "1,000.00" }),
        PaymentScreen.clickSendButton(),
    ].flat();
}

registry.category("web_tour.tours").add("PaymentScreenQRISPaymentFail", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            addProductandPay(),
            isQRDisplayedinDialog(),
            Dialog.confirm(),
            Dialog.is({ title: "QR payment pending" }),
        ].flat(),
});

registry.category("web_tour.tours").add("PaymentScreenQRISPaymentSuccess", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            addProductandPay(),
            isQRDisplayedinDialog(),
            Dialog.confirm(),
            FeedbackScreen.clickNextOrder(),
        ].flat(),
});

registry.category("web_tour.tours").add("PayementScreenQRISFetchQR", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            addProductandPay(),
            isQRDisplayedinDialog(),
            Dialog.discard(),
            PaymentScreen.clickCancelButton(),
            PaymentScreen.clickPaymentMethod("QRIS", true),
            PaymentScreen.clickSendButton(),
            isQRDisplayedinDialog(),
            Dialog.discard(),
            PaymentScreen.clickCancelButton(),
            PaymentScreen.clickRetryButton(),
            isQRDisplayedinDialog(),
        ].flat(),
});

registry.category("web_tour.tours").add("PayementScreenQRISChangeAmount", {
    steps: () =>
        [
            Chrome.startPoS(),
            addProductandPay(),
            isQRDisplayedinDialog(),
            Dialog.discard(),
            PaymentScreen.clickCancelButton(),
            PaymentScreen.clickBack(),
            ProductScreen.clickDisplayedProduct("Test Product"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentlineDelButton("QRIS", "1,000.00"),
            PaymentScreen.clickPaymentMethod("QRIS", true, { amount: "2,000.00" }),
            PaymentScreen.clickSendButton(),
            isQRDisplayedinDialog(),
            Dialog.discard(),
            PaymentScreen.clickCancelButton(),
            PaymentScreen.clickRetryButton(),
            isQRDisplayedinDialog(),
        ].flat(),
});
