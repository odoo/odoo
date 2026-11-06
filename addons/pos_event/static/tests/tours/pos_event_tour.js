// Part of Odoo. See LICENSE file for full copyright and licensing details.
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as FeedbackScreen from "@point_of_sale/../tests/pos/tours/utils/feedback_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as EventTourUtils from "@pos_event/../tests/tours/utils/event_tour_utils";
import * as SlotSelectionScreen from "@pos_event/../tests/tours/utils/slot_selection_screen_utils";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("EventAvailabilityInPos", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            // ------------------------- Limited Event ------------------------------
            // Check event limited (seats_max = 2), basic ticket unlimited, vip ticket max 1
            // - Taking 3 basic tickets should show error
            ProductScreen.clickDisplayedProduct("Event Limited"),
            EventTourUtils.increaseQuantityOfTicketBy("Ticket Basic", 3),
            Dialog.confirm(),
            Dialog.is({ title: "Event limit exceeded" }),
            Dialog.confirm(),
            // - Taking 3 different tickets should show error
            ProductScreen.clickDisplayedProduct("Event Limited"),
            EventTourUtils.increaseQuantityOfTicketBy("Ticket Basic", 2),
            EventTourUtils.increaseQuantityOfTicket("Ticket VIP"),
            Dialog.confirm(),
            Dialog.is({ title: "Event limit exceeded" }),
            Dialog.confirm(),
            // - Taking 2 vip tickets should show error
            ProductScreen.clickDisplayedProduct("Event Limited"),
            EventTourUtils.increaseQuantityOfTicketBy("Ticket VIP", 2),
            Dialog.confirm(),
            Dialog.is({ title: "Ticket limit exceeded" }),
            Dialog.confirm(),
            // - Taking 1 vip ticket should work
            ProductScreen.clickDisplayedProduct("Event Limited"),
            EventTourUtils.increaseQuantityOfTicket("Ticket VIP"),
            Dialog.confirm(),
            Dialog.is({ title: "Tickets" }),
            Dialog.confirm(),
            // - Taking 1 vip ticket (1 vip already in cart) should show error
            ProductScreen.clickDisplayedProduct("Event Limited"),
            EventTourUtils.increaseQuantityOfTicket("Ticket VIP"),
            Dialog.confirm(),
            Dialog.is({ title: "Ticket limit exceeded" }),
            Dialog.confirm(),
            // - Taking 1 basic ticket (1 vip already in cart) should work
            ProductScreen.clickDisplayedProduct("Event Limited"),
            EventTourUtils.increaseQuantityOfTicket("Ticket Basic"),
            Dialog.confirm(),
            Dialog.is({ title: "Tickets" }),
            Dialog.confirm(),
            // - Event should be sold out (seats_max = 2)
            ProductScreen.clickDisplayedProduct("Event Limited"),
            ProductScreen.clickDisplayedProduct("Event Limited"),
            {
                trigger: ".o_notification_bar.bg-danger",
            },
            // - Ending with 1 basic + 1 vip in cart

            // ------------------------- Unlimited Event ------------------------------
            // Check event unlimited, basic ticket unlimited (max 3 per selection), vip ticket max 1
            // - Taking 4 basic tickets should show error (limit max per order = 3)
            ProductScreen.clickDisplayedProduct("Event Unlimited"),
            EventTourUtils.increaseQuantityOfTicketBy("Ticket Basic", 4),
            Dialog.confirm(),
            Dialog.is({ title: "Ticket limit exceeded" }),
            Dialog.confirm(),
            // - Taking 2 vip tickets should show error
            ProductScreen.clickDisplayedProduct("Event Unlimited"),
            EventTourUtils.increaseQuantityOfTicketBy("Ticket VIP", 2),
            Dialog.confirm(),
            Dialog.is({ title: "Ticket limit exceeded" }),
            Dialog.confirm(),
            // - Taking 1 vip ticket and 3 basic tickets should work
            ProductScreen.clickDisplayedProduct("Event Unlimited"),
            EventTourUtils.increaseQuantityOfTicket("Ticket VIP"),
            EventTourUtils.increaseQuantityOfTicketBy("Ticket Basic", 3),
            Dialog.confirm(),
            Dialog.is({ title: "Tickets" }),
            Dialog.confirm(),
            // - Event shouldn't be sold out.
            // - Taking 1 vip ticket (1 vip already in cart) should show error
            ProductScreen.clickDisplayedProduct("Event Unlimited"),
            EventTourUtils.increaseQuantityOfTicket("Ticket VIP"),
            Dialog.confirm(),
            Dialog.is({ title: "Ticket limit exceeded" }),
            Dialog.confirm(),
            // - Ending with 3 basic + 1 vip in cart

            // ------------------------- Limited Multi Slot Event ------------------------------
            // Check slots limited (seats_max = 2), basic ticket unlimited, vip ticket max 1
            // Slot from 8-9AM
            // - Taking 3 basic tickets should show error
            ProductScreen.clickDisplayedProduct("MultiSlot Event Limited"),
            SlotSelectionScreen.clickDisplayedSlot("08:00"),
            Dialog.confirm(),
            EventTourUtils.increaseQuantityOfTicketBy("Ticket Basic", 3),
            Dialog.confirm(),
            Dialog.is({ title: "Slot limit exceeded" }),
            Dialog.confirm(),
            // - Taking 3 different tickets should show error
            ProductScreen.clickDisplayedProduct("MultiSlot Event Limited"),
            SlotSelectionScreen.clickDisplayedSlot("08:00"),
            Dialog.confirm(),
            EventTourUtils.increaseQuantityOfTicketBy("Ticket Basic", 2),
            EventTourUtils.increaseQuantityOfTicket("Ticket VIP"),
            Dialog.confirm(),
            Dialog.is({ title: "Slot limit exceeded" }),
            Dialog.confirm(),
            // - Taking 2 vip tickets should show error
            ProductScreen.clickDisplayedProduct("MultiSlot Event Limited"),
            SlotSelectionScreen.clickDisplayedSlot("08:00"),
            Dialog.confirm(),
            EventTourUtils.increaseQuantityOfTicketBy("Ticket VIP", 2),
            Dialog.confirm(),
            Dialog.is({ title: "Ticket limit exceeded" }),
            Dialog.confirm(),
            // - Taking 1 vip ticket should work
            ProductScreen.clickDisplayedProduct("MultiSlot Event Limited"),
            SlotSelectionScreen.clickDisplayedSlot("08:00"),
            Dialog.confirm(),
            EventTourUtils.increaseQuantityOfTicket("Ticket VIP"),
            Dialog.confirm(),
            Dialog.is({ title: "Tickets" }),
            Dialog.confirm(),
            // - Taking 1 vip ticket (1 vip already in cart) should show error
            ProductScreen.clickDisplayedProduct("MultiSlot Event Limited"),
            SlotSelectionScreen.clickDisplayedSlot("08:00"),
            Dialog.confirm(),
            EventTourUtils.increaseQuantityOfTicket("Ticket VIP"),
            Dialog.confirm(),
            Dialog.is({ title: "Ticket limit exceeded" }),
            Dialog.confirm(),
            // - Taking 1 basic ticket (1 vip already in cart) should work
            ProductScreen.clickDisplayedProduct("MultiSlot Event Limited"),
            SlotSelectionScreen.clickDisplayedSlot("08:00"),
            Dialog.confirm(),
            EventTourUtils.increaseQuantityOfTicket("Ticket Basic"),
            Dialog.confirm(),
            Dialog.is({ title: "Tickets" }),
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
            Dialog.is({ title: "Tickets" }),
            Dialog.confirm(),
            // - Both slots are sold out -> Event should be sold out (danger notification)
            ProductScreen.clickDisplayedProduct("MultiSlot Event Limited"),
            {
                trigger: ".o_notification_bar.bg-danger",
            },
            // - Ending with 2 basic + 2 vip in cart

            // ------------------------- Unlimited Multi Slot Event ------------------------------
            // Check slots unlimited, basic ticket unlimited, vip ticket max 1
            // Slot from 8-9AM
            // - Taking 4 basic tickets should show error (limit max per order = 3)
            ProductScreen.clickDisplayedProduct("MultiSlot Event Unlimited"),
            SlotSelectionScreen.clickDisplayedSlot("08:00"),
            Dialog.confirm(),
            EventTourUtils.increaseQuantityOfTicketBy("Ticket Basic", 4),
            Dialog.confirm(),
            Dialog.is({ title: "Ticket limit exceeded" }),
            Dialog.confirm(),
            // - Taking 2 vip tickets should show error
            ProductScreen.clickDisplayedProduct("MultiSlot Event Unlimited"),
            SlotSelectionScreen.clickDisplayedSlot("08:00"),
            Dialog.confirm(),
            EventTourUtils.increaseQuantityOfTicketBy("Ticket VIP", 2),
            Dialog.confirm(),
            Dialog.is({ title: "Ticket limit exceeded" }),
            Dialog.confirm(),
            // - Taking 3 basic tickets and 1 vip ticket should work
            ProductScreen.clickDisplayedProduct("MultiSlot Event Unlimited"),
            SlotSelectionScreen.clickDisplayedSlot("08:00"),
            Dialog.confirm(),
            EventTourUtils.increaseQuantityOfTicketBy("Ticket Basic", 3),
            EventTourUtils.increaseQuantityOfTicket("Ticket VIP"),
            Dialog.confirm(),
            Dialog.is({ title: "Tickets" }),
            Dialog.confirm(),
            // - Slot from 8-9AM shouldn't be sold out
            ProductScreen.clickDisplayedProduct("MultiSlot Event Unlimited"),
            SlotSelectionScreen.clickDisplayedSlot("08:00"),
            Dialog.confirm(),
            // - Taking 1 more vip ticket for the slot should show error (1 vip for the slot already in cart)
            EventTourUtils.increaseQuantityOfTicket("Ticket VIP"),
            Dialog.confirm(),
            Dialog.is({ title: "Ticket limit exceeded" }),
            Dialog.confirm(),
            // - Slot from 10-11AM should be available
            ProductScreen.clickDisplayedProduct("MultiSlot Event Unlimited"),
            SlotSelectionScreen.clickDisplayedSlot("10:00"),
            Dialog.confirm(),
            // - Taking 1 basic ticket and 1 vip ticket for the 10-11AM slot should work
            EventTourUtils.increaseQuantityOfTicket("Ticket Basic"),
            EventTourUtils.increaseQuantityOfTicket("Ticket VIP"),
            Dialog.confirm(),
            Dialog.is({ title: "Tickets" }),
            Dialog.confirm(),
            // - Ending with 4 basic + 2 vip in cart

            // Pay order
            ProductScreen.totalAmountIs("2,200.00"), // Event (4 basic + 2 vip = 800) + Multi slot Event (6 basic + 4 vip = 1400)
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank", true, { remaining: "0.00" }),
            PaymentScreen.clickValidate(),
            FeedbackScreen.isShown(),
            FeedbackScreen.printTicket("Full Page"),
            FeedbackScreen.printTicket("Badge"),
            FeedbackScreen.clickNextOrder(),
        ].flat(),
});

registry.category("web_tour.tours").add("EventQuestionsInPos", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("My Awesome Event"),
            EventTourUtils.increaseQuantityOfTicket("Ticket Basic"),
            EventTourUtils.increaseQuantityOfTicket("Ticket VIP"),
            Dialog.confirm(),
            Dialog.is({ title: "Tickets" }),
            // Global
            EventTourUtils.answerGlobalTextQuestion("Text Q1", "Q1-Answer"),
            EventTourUtils.answerGlobalSelectQuestion("Choice Q3", "Q3-Answer1"),
            // Ticket 1
            EventTourUtils.answerTicketQuestion("1", "Name", "Name 1"),
            EventTourUtils.answerTicketQuestion("1", "Email", "email1@example.com"),
            EventTourUtils.answerTicketQuestion("1", "Text Q2", "Q2-Answer1"),
            EventTourUtils.answerTicketSelectQuestion("1", "Choice Q4", "Q4-Answer1"),
            // Ticket 2
            EventTourUtils.answerTicketQuestion("2", "Name", "Name 2"),
            EventTourUtils.answerTicketQuestion("2", "Text Q2", "Q2-Answer2"),
            {
                content: `confirm button is disabled`,
                trigger: `.modal-footer .btn-primary:disabled`,
            },
            EventTourUtils.answerTicketQuestion("2", "Email", "email2@example.com"),
            {
                content: `confirm button is disabled`,
                trigger: `.modal-footer .btn-primary:disabled`,
            },
            EventTourUtils.answerTicketSelectQuestion("2", "Choice Q4", "Q4-Answer2"),
            {
                content: `confirm button is enabled`,
                trigger: `.modal-footer .btn-primary:not(:disabled)`,
            },
            Dialog.confirm(),
            // Long press the Ticket Basic order line to edit its registration answers.
            ProductScreen.longPressOrderline("Event Ticket"),
            EventTourUtils.answerTicketQuestion("1", "Name", "Name 1 edited"),
            EventTourUtils.answerTicketQuestion("1", "Text Q2", "Q2-Answer1 edited"),
            Dialog.confirm(),

            // ------------------------- Multi Slot Event ------------------------------
            ProductScreen.clickDisplayedProduct("My Awesome MultiSlot Event"),
            SlotSelectionScreen.clickDisplayedSlot("08:00"),
            Dialog.confirm(),
            EventTourUtils.increaseQuantityOfTicket("Ticket Basic"),
            Dialog.confirm(),
            Dialog.is({ title: "Tickets" }),
            // Global
            EventTourUtils.answerGlobalTextQuestion("Text Q1", "Q1-Answer"),
            EventTourUtils.answerGlobalSelectQuestion("Choice Q3", "Q3-Answer2"),
            // Ticket 1
            EventTourUtils.answerTicketQuestion("1", "Name", "Name 3"),
            EventTourUtils.answerTicketQuestion("1", "Email", "email3@example.com"),
            EventTourUtils.answerTicketQuestion("1", "Text Q2", "Q2-Answer3"),
            EventTourUtils.answerTicketSelectQuestion("1", "Choice Q4", "Q4-Answer1"),
            Dialog.confirm(),

            // The ticket price must remain the same after setting a customer with a pricelist
            ProductScreen.totalAmountIs("400.00"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Partner Test 1"),
            ProductScreen.totalAmountIs("400.00"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank", true, { remaining: "0.00" }),
            PaymentScreen.clickValidate(),
            FeedbackScreen.isShown(),
        ].flat(),
});

registry.category("web_tour.tours").add("EventRegistrationNotMandatoryInPos", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            // No customer, all information filled
            ProductScreen.clickDisplayedProduct("Event regitration not mandatory"),
            EventTourUtils.increaseQuantityOfTicket("Ticket Basic"),
            Dialog.confirm(),
            Dialog.is({ title: "Tickets" }),
            EventTourUtils.answerGlobalTextQuestion("Name", "Name 1"),
            EventTourUtils.answerGlobalTextQuestion("Email", "1@test.com"),
            EventTourUtils.answerGlobalTextQuestion("Phone", "1234567890"),
            Dialog.confirm(),
            ProductScreen.longPressOrderline("Event Ticket"),
            EventTourUtils.answerGlobalTextQuestion("Name", "TEST"),
            EventTourUtils.answerGlobalTextQuestion("Email", "2@test.com"),
            Dialog.confirm(),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            FeedbackScreen.clickNextOrder(),

            // Customer given, all information filled
            ProductScreen.clickDisplayedProduct("Event regitration not mandatory"),
            EventTourUtils.increaseQuantityOfTicket("Ticket Basic"),
            Dialog.confirm(),
            Dialog.is({ title: "Tickets" }),
            EventTourUtils.answerGlobalTextQuestion("Name", "Name 2"),
            EventTourUtils.answerGlobalTextQuestion("Email", "2@test.com"),
            EventTourUtils.answerGlobalTextQuestion("Phone", "+99999999"),
            Dialog.confirm(),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Event Partner"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            FeedbackScreen.clickNextOrder(),

            // Customer given, partial information filled
            ProductScreen.clickDisplayedProduct("Event regitration not mandatory"),
            EventTourUtils.increaseQuantityOfTicket("Ticket Basic"),
            Dialog.confirm(),
            Dialog.is({ title: "Tickets" }),
            EventTourUtils.answerGlobalTextQuestion("Name", "Name 3"),
            Dialog.confirm(),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Event Partner"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            FeedbackScreen.clickNextOrder(),

            // Customer given, partial information filled
            ProductScreen.clickDisplayedProduct("Event regitration not mandatory"),
            EventTourUtils.increaseQuantityOfTicket("Ticket Basic"),
            Dialog.confirm(),
            {
                trigger: ".ticket_question",
            },
            Dialog.confirm(),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Event Partner"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            FeedbackScreen.clickNextOrder(),
        ].flat(),
});
