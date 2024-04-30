// Part of Odoo. See LICENSE file for full copyright and licensing details.
import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as ReceiptScreen from "@point_of_sale/../tests/tours/utils/receipt_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/tours/utils/payment_screen_util";
import * as EventTourUtils from "@pos_event/../tests/tours/utils/event_tour_utils";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("SellingEventInPos", {
    test: true,
    steps: () =>
        [
            Dialog.confirm("Open session"),
            // Buy a VIP Ticket
            ProductScreen.clickDisplayedProduct("My Awesome Event"),
            EventTourUtils.increaseQuantity(),
            EventTourUtils.pickTicket("Event Ticket VIP"),
            // Confirm popup - There isn't enough tickets available
            Dialog.confirm(),
            EventTourUtils.decreaseQuantity(),
            EventTourUtils.pickTicket("Event Ticket VIP"),
            ProductScreen.totalAmountIs("200.00"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank", true, { remaining: "0.00" }),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            EventTourUtils.printTicket("full"),
            EventTourUtils.printTicket("badge"),
            ReceiptScreen.clickNextOrder(),
            // Buy a Basic Ticket
            ProductScreen.clickDisplayedProduct("My Awesome Event"),
            EventTourUtils.pickTicket("Event Ticket VIP"),
            Dialog.confirm(),
            EventTourUtils.pickTicket("Event Ticket Basic"),
            ProductScreen.totalAmountIs("100.00"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank", true, { remaining: "0.00" }),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            ReceiptScreen.clickNextOrder(),
            EventTourUtils.eventRemainingSeat("My Awesome Event", 0),
        ].flat(),
});
