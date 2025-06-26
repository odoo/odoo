import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/tours/utils/payment_screen_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import * as ReceiptScreen from "@point_of_sale/../tests/tours/utils/receipt_screen_util";
import * as Chrome from "@point_of_sale/../tests/tours/utils/chrome_util";

import { registry } from "@web/core/registry";

function isQRDisplayedinDialog() {
    return [
        Dialog.is({ title: "QR Code" }),
        {
            content: "Verify QR image is displayed",
            trigger: ".modal-content img[src^='data:image/png;base64,']",
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
        {
            content: "Display QR Code Payment dialog",
            trigger: ".button.send_payment_request.highlight",
            run: "click",
        },
    ].flat();
}

registry.category("web_tour.tours").add("PaymentScreenQRISPaymentFail", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            addProductandPay(),
            isQRDisplayedinDialog(),
            Dialog.confirm("Confirm Payment"),
            Dialog.is({ title: "Payment Status Update" }),
        ].flat(),
});

registry.category("web_tour.tours").add("PaymentScreenQRISPaymentSuccess", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            addProductandPay(),
            isQRDisplayedinDialog(),
            Dialog.confirm("Confirm Payment"),
            ReceiptScreen.clickNextOrder(),
        ].flat(),
});

registry.category("web_tour.tours").add("PayementScreenQRISFetchQR", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            addProductandPay(),
            isQRDisplayedinDialog(),
            Dialog.cancel(),
            PaymentScreen.clickPaymentMethod("QRIS", true),
            {
                isActive: ["body:has(.modal)"],
                content: "close error modal: there is already an electronic payment in progress",
                trigger: ".modal .btn:contains(ok)",
                run: "click",
            },
            {
                content: "Display QR Code Payment dialog",
                trigger: ".button.send_payment_request.highlight",
                run: "click",
            },
        ].flat(),
});

registry.category("web_tour.tours").add("PayementScreenQRISChangeAmount", {
    steps: () =>
        [
            Chrome.startPoS(),
            addProductandPay(),
            isQRDisplayedinDialog(),
            Dialog.cancel(),
            PaymentScreen.clickBack(),
            ProductScreen.clickDisplayedProduct("Test Product"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentlineDelButton("QRIS", "1,000.00"),
            PaymentScreen.clickPaymentMethod("QRIS", true, { amount: "2,000.00" }),
            {
                isActive: ["body:has(.modal)"],
                content: "close error modal: there is already an electronic payment in progress",
                trigger: ".modal .btn:contains(ok)",
                run: "click",
            },
            {
                content: "Display QR Code Payment dialog",
                trigger: ".button.send_payment_request.highlight",
                run: "click",
            },
        ].flat(),
});
