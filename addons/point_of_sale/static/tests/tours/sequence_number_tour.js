import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as ReceiptScreen from "@point_of_sale/../tests/tours/utils/receipt_screen_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import * as PaymentScreen from "@point_of_sale/../tests/tours/utils/payment_screen_util";
import * as TicketScreen from "@point_of_sale/../tests/tours/utils/ticket_screen_util";
import * as Chrome from "@point_of_sale/../tests/tours/utils/chrome_util";
import { openRegister } from "@point_of_sale/../tests/tours/utils/common";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("SequenceNumberTour.1", {
    test: true,
    steps: () =>
        [
            Dialog.confirm("Open session"),

            // Order 1 is at Product Screen
            ProductScreen.clickDisplayedProduct("Desk Pad"),
            Chrome.clickMenuOption("Orders"),
            TicketScreen.checkStatus("-0001", "Ongoing"),

            // Order 2 is at Payment Screen
            TicketScreen.clickNewTicket(),
            ProductScreen.clickDisplayedProduct("Monitor Stand"),
            ProductScreen.clickPayButton(),
            PaymentScreen.isShown(),
            Chrome.clickMenuOption("Orders"),
            TicketScreen.checkStatus("-0002", "Payment"),

            // Order 3 is at Receipt Screen
            TicketScreen.clickNewTicket(),
            ProductScreen.clickDisplayedProduct("Whiteboard Pen"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank", true, { remaining: "0.0" }),
            PaymentScreen.validateButtonIsHighlighted(true),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            Chrome.clickMenuOption("Orders"),
            TicketScreen.checkStatus("-0003", "Receipt"),

            // Order 4 is at Product Screen
            TicketScreen.clickNewTicket(),
            ProductScreen.clickDisplayedProduct("Desk Pad"),
            Chrome.clickMenuOption("Orders"),
            TicketScreen.checkStatus("-0004", "Ongoing"),
        ].flat(),
});

registry.category("web_tour.tours").add("SequenceNumberTour.2", {
    test: true,
    steps: () =>
        [
            Dialog.confirm("Open session"),

            ProductScreen.clickDisplayedProduct("Whiteboard Pen"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank", true, { remaining: "0.0" }),
            PaymentScreen.validateButtonIsHighlighted(true),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            Chrome.clickMenuOption("Orders"),
            TicketScreen.checkStatus("-0001", "Receipt"),

            Chrome.clickMenuOption("Backend"),

            openRegister(),

            ProductScreen.clickDisplayedProduct("Monitor Stand"),
            Chrome.clickMenuOption("Orders"),
            TicketScreen.checkStatus("-0002", "Ongoing"),
        ].flat(),
});
