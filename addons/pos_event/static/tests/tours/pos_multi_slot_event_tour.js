// Part of Odoo. See LICENSE file for full copyright and licensing details.
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as ReceiptScreen from "@point_of_sale/../tests/pos/tours/utils/receipt_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as SlotSelectionScreen from "@pos_event/../tests/tours/utils/slot_selection_screen_utils";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as EventTourUtils from "@pos_event/../tests/tours/utils/event_tour_utils";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("MultiSlotEventAvailabilityInPos", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            // Check slots seats limited (seats_max = 2), basic ticket unlimited, vip ticket max 1
            // Slot from 8-9AM
            // - Taking 3 basic tickets should show error
            ProductScreen.clickDisplayedProduct("MultiSlot Event Limited"),
            SlotSelectionScreen.clickDisplayedSlot("08:00"),
            Dialog.confirm(),
            EventTourUtils.increaseQuantityOfTicketBy("Ticket Basic", 3),
            Dialog.confirm(),
            Dialog.confirm(),
            // - Taking 3 different tickets should show error
            ProductScreen.clickDisplayedProduct("MultiSlot Event Limited"),
            SlotSelectionScreen.clickDisplayedSlot("08:00"),
            Dialog.confirm(),
            EventTourUtils.increaseQuantityOfTicketBy("Ticket Basic", 2),
            EventTourUtils.increaseQuantityOfTicket("Ticket VIP"),
            Dialog.confirm(),
            Dialog.confirm(),
            // - Taking 2 vip tickets should show error
            ProductScreen.clickDisplayedProduct("MultiSlot Event Limited"),
            SlotSelectionScreen.clickDisplayedSlot("08:00"),
            Dialog.confirm(),
            EventTourUtils.increaseQuantityOfTicketBy("Ticket VIP", 2),
            Dialog.confirm(),
            Dialog.confirm(),
            // - Taking 1 vip ticket should work
            ProductScreen.clickDisplayedProduct("MultiSlot Event Limited"),
            SlotSelectionScreen.clickDisplayedSlot("08:00"),
            Dialog.confirm(),
            EventTourUtils.increaseQuantityOfTicket("Ticket VIP"),
            Dialog.confirm(),
            EventTourUtils.answerTicketSelectQuestion("1", "Question1", "Q1-Answer1"),
            EventTourUtils.answerGlobalSelectQuestion("Question2", "Q2-Answer1"),
            Dialog.confirm(),
            // - Taking 1 vip ticket (1 vip already in cart) should show error
            ProductScreen.clickDisplayedProduct("MultiSlot Event Limited"),
            SlotSelectionScreen.clickDisplayedSlot("08:00"),
            Dialog.confirm(),
            EventTourUtils.increaseQuantityOfTicket("Ticket VIP"),
            Dialog.confirm(),
            Dialog.confirm(),
            // - Taking 1 basic ticket (1 vip already in cart) should work
            ProductScreen.clickDisplayedProduct("MultiSlot Event Limited"),
            SlotSelectionScreen.clickDisplayedSlot("08:00"),
            Dialog.confirm(),
            EventTourUtils.increaseQuantityOfTicket("Ticket Basic"),
            Dialog.confirm(),
            EventTourUtils.answerTicketSelectQuestion("1", "Question1", "Q1-Answer1"),
            EventTourUtils.answerGlobalSelectQuestion("Question2", "Q2-Answer1"),
            Dialog.confirm(),
            // - Slot from 8-9AM should be sold out
            ProductScreen.clickDisplayedProduct("MultiSlot Event Limited"),
            SlotSelectionScreen.assertDisabledSlot("08:00"),
            // - Slot from 10-11AM should still be available
            SlotSelectionScreen.clickDisplayedSlot("10:00"),
            Dialog.confirm(),
            // - Taking every available tickets for the 10-11AM slot should work
            EventTourUtils.increaseQuantityOfTicket("Ticket Basic"),
            EventTourUtils.increaseQuantityOfTicket("Ticket VIP"),
            Dialog.confirm(),
            EventTourUtils.answerTicketSelectQuestion("1", "Question1", "Q1-Answer1"),
            EventTourUtils.answerGlobalSelectQuestion("Question2", "Q2-Answer1"),
            Dialog.confirm(),
            // - Both slots are sold out -> Event should be sold out (danger notification)
            ProductScreen.clickDisplayedProduct("MultiSlot Event Limited"),
            {
                trigger: ".o_notification_bar.bg-danger",
            },
            // - Ending with 2 basic + 2 vip in cart

            // --------------------------------------------------------------------

            // Check slots seats unlimited, basic ticket unlimited, vip ticket max 1
            // Slot from 8-9AM
            // - Taking 2 vip tickets should show error
            ProductScreen.clickDisplayedProduct("MultiSlot Event Unlimited"),
            SlotSelectionScreen.clickDisplayedSlot("08:00"),
            Dialog.confirm(),
            EventTourUtils.increaseQuantityOfTicketBy("Ticket VIP", 2),
            Dialog.confirm(),
            Dialog.confirm(),
            // - Taking 3 basic tickets and 1 vip ticket should work
            ProductScreen.clickDisplayedProduct("MultiSlot Event Unlimited"),
            SlotSelectionScreen.clickDisplayedSlot("08:00"),
            Dialog.confirm(),
            EventTourUtils.increaseQuantityOfTicketBy("Ticket Basic", 3),
            EventTourUtils.increaseQuantityOfTicket("Ticket VIP"),
            Dialog.confirm(),
            EventTourUtils.answerTicketSelectQuestion("1", "Question1", "Q1-Answer1"),
            EventTourUtils.answerGlobalSelectQuestion("Question2", "Q2-Answer1"),
            Dialog.confirm(),
            // - Slot from 8-9AM shouldn't be sold out
            ProductScreen.clickDisplayedProduct("MultiSlot Event Unlimited"),
            SlotSelectionScreen.clickDisplayedSlot("08:00"),
            Dialog.confirm(),
            // - Taking 1 more vip ticket for the slot should show error (1 vip for the slot already in cart)
            EventTourUtils.increaseQuantityOfTicket("Ticket VIP"),
            Dialog.confirm(),
            Dialog.confirm(),
            // - Slot from 10-11AM should be available
            ProductScreen.clickDisplayedProduct("MultiSlot Event Unlimited"),
            SlotSelectionScreen.clickDisplayedSlot("10:00"),
            Dialog.confirm(),
            // - Taking 1 basic ticket and 1 vip ticket for the 10-11AM slot should work
            EventTourUtils.increaseQuantityOfTicket("Ticket Basic"),
            EventTourUtils.increaseQuantityOfTicket("Ticket VIP"),
            Dialog.confirm(),
            EventTourUtils.answerTicketSelectQuestion("1", "Question1", "Q1-Answer1"),
            EventTourUtils.answerGlobalSelectQuestion("Question2", "Q2-Answer1"),
            Dialog.confirm(),
            // - Ending with 4 basic + 2 vip in cart

            // Pay order
            ProductScreen.totalAmountIs("1,400.00"), // (6 basic + 4 vip)
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank", true, { remaining: "0.00" }),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            EventTourUtils.printTicket("full"),
            EventTourUtils.printTicket("badge"),
            ReceiptScreen.clickNextOrder(),
        ].flat(),
});

registry.category("web_tour.tours").add("SellingMultiSlotEventInPos", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            // Confirm popup - Not enough tickets available for this choice
            ProductScreen.clickDisplayedProduct("My Awesome MultiSlot Event"),
            SlotSelectionScreen.clickDisplayedSlot("08:00"),
            Dialog.confirm(),
            EventTourUtils.increaseQuantityOfTicket("Ticket Basic"),
            Dialog.confirm(),
            Dialog.confirm(),

            // Confirm popup - Not enough tickets available for this ticket
            ProductScreen.clickDisplayedProduct("My Awesome MultiSlot Event"),
            SlotSelectionScreen.clickDisplayedSlot("10:00"),
            Dialog.confirm(),
            EventTourUtils.increaseQuantityOfTicketBy("Ticket VIP", 2),
            Dialog.confirm(),
            Dialog.confirm(),

            // Confirm popup - Enough availability
            ProductScreen.clickDisplayedProduct("My Awesome MultiSlot Event"),
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
            ProductScreen.clickDisplayedProduct("My Awesome MultiSlot Event"),
            SlotSelectionScreen.assertDisabledSlot("08:00"),
        ].flat(),
});
