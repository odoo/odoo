// Part of Odoo. See LICENSE file for full copyright and licensing details.
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as ReceiptScreen from "@point_of_sale/../tests/pos/tours/utils/receipt_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as SlotSelectionScreen from "@pos_event/../tests/tours/utils/slot_selection_screen_utils";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as EventTourUtils from "@pos_event/../tests/tours/utils/event_tour_utils";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("SellingMultiSlotEventInPos", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            // Confirm popup - Not enough tickets available for this choice
            ProductScreen.clickDisplayedProduct("My Awesome Event"),
            SlotSelectionScreen.clickDisplayedSlot("08:00"),
            Dialog.confirm(),
            EventTourUtils.increaseQuantityOfTicket("Ticket Basic"),
            Dialog.confirm(),
            Dialog.confirm(),

            // Confirm popup - Not enough tickets available for this ticket
            ProductScreen.clickDisplayedProduct("My Awesome Event"),
            SlotSelectionScreen.clickDisplayedSlot("10:00"),
            Dialog.confirm(),
            EventTourUtils.increaseQuantityOfTicket("Ticket VIP"),
            EventTourUtils.increaseQuantityOfTicket("Ticket VIP"),
            Dialog.confirm(),
            Dialog.confirm(),

            // Confirm popup - Enough availability
            ProductScreen.clickDisplayedProduct("My Awesome Event"),
            SlotSelectionScreen.clickDisplayedSlot("08:00"),
            Dialog.confirm(),
            EventTourUtils.increaseQuantityOfTicket("Ticket VIP"),
            Dialog.confirm(),
            EventTourUtils.answerTicketSelectQuestion("1", "Question1", "Q1-Answer1"),
            EventTourUtils.answerGlobalSelectQuestion("Question2", "Q2-Answer1"),
            Dialog.confirm(),
            ProductScreen.totalAmountIs("200.00"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank", true, { remaining: "0.00" }),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            EventTourUtils.printTicket("full"),
            EventTourUtils.printTicket("badge"),
            ReceiptScreen.clickNextOrder(),

            // Slot is now unavailable
            ProductScreen.clickDisplayedProduct("My Awesome Event"),
            SlotSelectionScreen.assertDisabledSlot("08:00"),
        ].flat(),
});
