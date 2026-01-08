/** @odoo-module */

import * as ProductScreen from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import * as ReceiptScreen from "@point_of_sale/../tests/tours/helpers/ReceiptScreenTourMethods";
import * as PaymentScreen from "@point_of_sale/../tests/tours/helpers/PaymentScreenTourMethods";
import * as TicketScreen from "@point_of_sale/../tests/tours/helpers/TicketScreenTourMethods";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("spanish_pos_tbai_tour", {
    test: true,
    steps: () => [
        ProductScreen.confirmOpeningPopup(),
        ProductScreen.clickHomeCategory(),
        ProductScreen.clickDisplayedProduct("Desk Pad"),
        ProductScreen.clickPayButton(),
        PaymentScreen.clickPaymentMethod("Bank"),
        PaymentScreen.remainingIs("0.00"),
        PaymentScreen.clickValidate(),
        ReceiptScreen.isShown(),
        ReceiptScreen.clickNextOrder(),
        ProductScreen.clickRefund(),
        TicketScreen.selectOrder("-0001"),
        ProductScreen.pressNumpad("1"),
        TicketScreen.toRefundTextContains("To Refund: 1.00"),
        TicketScreen.confirmRefund(),
        {
            trigger: 'button:contains("R1")',
        },
        ProductScreen.isShown(),
        ProductScreen.clickPayButton(),
        PaymentScreen.clickPaymentMethod("Bank"),
        PaymentScreen.clickValidate(),
        ReceiptScreen.isShown(),
    ].flat(),
});
