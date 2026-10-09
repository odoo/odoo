// Part of Odoo. See LICENSE file for full copyright and licensing details.
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as FeedbackScreen from "@point_of_sale/../tests/pos/tours/utils/feedback_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as EventTourUtils from "@pos_event/../tests/tours/utils/event_tour_utils";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("SellingEventInPosWithChoiceAnswers", {
    steps: () =>
        [
            Chrome.startPoS(),
            // Confirm popup - There isn't enough tickets available
            ProductScreen.clickDisplayedProduct("My Awesome Event"),
            EventTourUtils.increaseQuantityOfTicket("Ticket VIP"),
            EventTourUtils.increaseQuantityOfTicket("Ticket VIP"),
            Dialog.is({ title: "Tickets" }),
            Dialog.confirm("Confirm"),
            Dialog.is({ title: "Ticket limit exceeded" }),
            Dialog.confirm("Ok"),

            // Buy a VIP Ticket
            ProductScreen.clickDisplayedProduct("My Awesome Event"),
            EventTourUtils.increaseQuantityOfTicket("Ticket VIP"),
            Dialog.is({ title: "Tickets" }),
            Dialog.confirm("Confirm"),
            EventTourUtils.answerTicketSelectQuestion("1", "Question1", "Q1-Answer1"),
            EventTourUtils.answerGlobalSelectQuestion("Question2", "Q2-Answer1"),
            {
                content: `confirm button is disabled`,
                trigger: `.modal-footer .btn-primary:disabled`,
            },
            EventTourUtils.answerGlobalSelectQuestion("Question3", "Q3-Answer1"),
            Dialog.is({ title: "Tickets" }),
            {
                content: `confirm button is enabled`,
                trigger: `.modal-footer .btn-primary:not(:disabled)`,
            },
            Dialog.confirm("Confirm"),
            ProductScreen.totalAmountIs("200.00"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank", true, { remaining: "0.00" }),
            PaymentScreen.clickValidate(),
            FeedbackScreen.isShown(),
            FeedbackScreen.printTicket("Full Page"),
            FeedbackScreen.printTicket("Badge"),
            FeedbackScreen.clickNextOrder(),
        ].flat(),
});

registry.category("web_tour.tours").add("SellingEventInPosWithTextAnswers", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            // Buy a VIP Ticket
            ProductScreen.clickDisplayedProduct("My Awesome Event"),
            EventTourUtils.increaseQuantityOfTicket("Ticket VIP"),
            EventTourUtils.increaseQuantityOfTicket("Ticket VIP"),
            Dialog.confirm(),
            EventTourUtils.answerGlobalTextQuestion("Text Box 1", "TB1-Answer"),
            EventTourUtils.answerTicketQuestion("1", "Text Box 2", "T1-TB2-Answer"),
            EventTourUtils.answerTicketQuestion("2", "Text Box 2", "T2-TB2-Answer"),
            Dialog.confirm(),
            ProductScreen.totalAmountIs("400.00"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank", true, { remaining: "0.00" }),
            PaymentScreen.clickValidate(),
            FeedbackScreen.isShown(),
        ].flat(),
});

registry.category("web_tour.tours").add("CheckEventAvailability", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            // Check event seats limited (seats_max = 2), basic ticket unlimited, vip ticket max 1
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
            EventTourUtils.answerTicketSelectQuestion("1", "Question1", "Q1-Answer1"),
            EventTourUtils.answerGlobalSelectQuestion("Question2", "Q2-Answer1"),
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
            EventTourUtils.answerTicketSelectQuestion("1", "Question1", "Q1-Answer1"),
            EventTourUtils.answerGlobalSelectQuestion("Question2", "Q2-Answer1"),
            Dialog.confirm(),
            // - Event should be sold out (seats_max = 2)
            ProductScreen.clickDisplayedProduct("Event Limited"),
            ProductScreen.clickDisplayedProduct("Event Limited"),
            {
                trigger: ".o_notification_bar.bg-danger",
            },
            // - Ending with 1 basic + 1 vip in cart

            // --------------------------------------------------------------------

            // Check event seats unlimited, basic ticket unlimited (max 3 per selection), vip ticket max 1
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
            EventTourUtils.answerTicketSelectQuestion("1", "Question1", "Q1-Answer1"),
            EventTourUtils.answerGlobalSelectQuestion("Question2", "Q2-Answer1"),
            Dialog.confirm(),
            // - Event shouldn't be sold out.
            // - Taking 1 vip ticket (1 vip already in cart) should show error
            ProductScreen.clickDisplayedProduct("Event Unlimited"),
            EventTourUtils.increaseQuantityOfTicket("Ticket VIP"),
            Dialog.confirm(),
            Dialog.is({ title: "Ticket limit exceeded" }),
            Dialog.confirm(),
            // - Ending with 3 basic + 1 vip in cart

            // Pay order
            ProductScreen.totalAmountIs("800.00"), // (4 basic + 2 vip)
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank", true, { remaining: "0.00" }),
            PaymentScreen.clickValidate(),
            FeedbackScreen.isShown(),
            FeedbackScreen.printTicket("Full Page"),
            FeedbackScreen.printTicket("Badge"),
            FeedbackScreen.clickNextOrder(),
        ].flat(),
});

registry.category("web_tour.tours").add("CheckEventTicketPrice", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("My Awesome Event"),
            EventTourUtils.increaseQuantityOfTicket("Ticket Basic"),
            Dialog.confirm(),
            EventTourUtils.answerTicketSelectQuestion("1", "Question1", "Q1-Answer1"),
            EventTourUtils.answerGlobalSelectQuestion("Question2", "Q2-Answer1"),
            Dialog.confirm(),
            ProductScreen.totalAmountIs("100.00"),
            ProductScreen.clickPriceList("Special Pricelist"),
            ProductScreen.totalAmountIs("80.00"),
            ProductScreen.clickDisplayedProduct("My Awesome Event"),
            EventTourUtils.increaseQuantityOfTicket("Ticket VIP"),
            Dialog.confirm(),
            EventTourUtils.answerTicketSelectQuestion("1", "Question1", "Q1-Answer1"),
            EventTourUtils.answerGlobalSelectQuestion("Question2", "Q2-Answer1"),
            Dialog.confirm(),
            ProductScreen.totalAmountIs("160.00"),
            ProductScreen.clickPriceList("Test Pricelist"),
            ProductScreen.totalAmountIs("300.00"),
        ].flat(),
});

registry.category("web_tour.tours").add("test_selling_multiple_ticket_saved", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("My Awesome Event"),
            EventTourUtils.increaseQuantityOfTicket("Ticket VIP"),
            EventTourUtils.increaseQuantityOfTicket("Ticket Basic"),
            Dialog.confirm(),
            EventTourUtils.answerTicketSelectQuestion("1", "Question1", "Q1-Answer1"),
            EventTourUtils.answerTicketSelectQuestion("2", "Question1", "Q1-Answer1"),
            EventTourUtils.answerGlobalSelectQuestion("Question2", "Q2-Answer1"),
            Dialog.confirm(),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank", true, { remaining: "0.00" }),
            PaymentScreen.clickValidate(),
            FeedbackScreen.isShown(),
            FeedbackScreen.printTicket("Full Page"),
            FeedbackScreen.printTicket("Badge"),
            FeedbackScreen.clickNextOrder(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_orderline_price_remain_same_as_ticket_price", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            ProductScreen.clickDisplayedProduct("My Awesome Event"),
            EventTourUtils.increaseQuantityOfTicket("Ticket VIP"),
            Dialog.confirm(),
            EventTourUtils.answerTicketSelectQuestion("1", "Question1", "Q1-Answer1"),
            EventTourUtils.answerGlobalSelectQuestion("Question2", "Q2-Answer1"),
            Dialog.confirm(),
            ProductScreen.totalAmountIs("200.00"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Partner Test 1"),
            ProductScreen.totalAmountIs("200.00"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank", true, { remaining: "0.00" }),
            PaymentScreen.clickValidate(),
            FeedbackScreen.isShown(),
            FeedbackScreen.printTicket("Full Page"),
            FeedbackScreen.printTicket("Badge"),
            FeedbackScreen.clickNextOrder(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_pos_event_registration_not_mandatory", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            // No customer, all information filled
            ProductScreen.clickDisplayedProduct("Event regitration not mandatory"),
            EventTourUtils.increaseQuantityOfTicket("Ticket Basic"),
            Dialog.confirm(),
            {
                trigger: ".ticket_question",
            },
            EventTourUtils.answerGlobalTextQuestion("Name", "Name 1"),
            EventTourUtils.answerGlobalTextQuestion("Email", "1@test.com"),
            EventTourUtils.answerGlobalTextQuestion("Phone", "1234567890"),
            Dialog.confirm(),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            FeedbackScreen.clickNextOrder(),

            // Customer given, all information filled
            ProductScreen.clickDisplayedProduct("Event regitration not mandatory"),
            EventTourUtils.increaseQuantityOfTicket("Ticket Basic"),
            Dialog.confirm(),
            {
                trigger: ".ticket_question",
            },
            EventTourUtils.answerGlobalTextQuestion("Name", "Name 2"),
            EventTourUtils.answerGlobalTextQuestion("Email", "2@test.com"),
            EventTourUtils.answerGlobalTextQuestion("Phone", "+99999999"),
            Dialog.confirm(),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Event Parter"),
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
            EventTourUtils.answerGlobalTextQuestion("Name", "Name 3"),
            Dialog.confirm(),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Event Parter"),
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
            ProductScreen.clickCustomer("Event Parter"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            FeedbackScreen.clickNextOrder(),
        ].flat(),
});
