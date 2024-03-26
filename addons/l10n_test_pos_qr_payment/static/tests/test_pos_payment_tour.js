/** @odoo-module */

import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/tours/utils/payment_screen_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";

import { registry } from "@web/core/registry";

/**
 * HELPERS
 */

function isQRDisplayedinDialog() {
    return [
        Dialog.is({ title: "QR Code" }),
        {
            content: "Verify QR image is displayed",
            trigger: ".modal-content img[src^='data:image/png;base64,']",
        },
    ].flat();
}

function addProductandPay() {
    return [
        ProductScreen.addOrderline("Hand Bag", "10"),
        ProductScreen.selectedOrderlineHas("Hand Bag", "10.0"),
        ProductScreen.clickPayButton(),

        PaymentScreen.totalIs("48"),
        PaymentScreen.clickPaymentMethod("QR Code", true, { amount: "48" }),
        {
            content: "Display QR Code Payment dialog",
            trigger: ".button.send_payment_request.highlight",
        },
    ].flat();
}

/**
 * TOURS
 */

registry.category("web_tour.tours").add("PaymentScreenWithQRPaymentFailure", {
    test: true,
    steps: () =>
        [
            addProductandPay(),
            Dialog.is({ title: "Failure to generate Payment QR Code" }),
            Dialog.confirm(),
        ].flat(),
});

registry.category("web_tour.tours").add("PaymentScreenWithQRPayment", {
    test: true,
    steps: () =>
        [
            addProductandPay(),
            isQRDisplayedinDialog(),
            Dialog.cancel(),
            PaymentScreen.validateButtonIsHighlighted(false),
            {
                content: "Retry to display QR Code Payment dialog",
                trigger: ".button.send_payment_request.highlight",
            },
            isQRDisplayedinDialog(),
            Dialog.confirm(),
            {
                content: "Immediately at the receipt screen.",
                trigger: '.receipt-screen .button.next.highlight:contains("New Order")',
            },
        ].flat(),
});

registry.category("web_tour.tours").add("PaymentScreenWithQRPaymentSwiss", {
    test: true,
    steps: () =>
        [
            ProductScreen.addOrderline("Hand Bag", "10"),
            ProductScreen.selectedOrderlineHas("Hand Bag", "10.0"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("AAA Partner Swiss"),
            ProductScreen.clickPayButton(),
            PaymentScreen.totalIs("48"),
            PaymentScreen.clickPaymentMethod("QR Code", true, { amount: "48" }),
            {
                content: "Display QR Code Payment dialog",
                trigger: ".button.send_payment_request.highlight",
            },
            PaymentScreen.validateButtonIsHighlighted(false),
            isQRDisplayedinDialog(),
            Dialog.confirm(),
            {
                content: "Immediately at the receipt screen.",
                trigger: '.receipt-screen .button.next.highlight:contains("New Order")',
            },
        ].flat(),
});
