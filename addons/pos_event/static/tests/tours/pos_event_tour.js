// Part of Odoo. See LICENSE file for full copyright and licensing details.
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as FeedbackScreen from "@point_of_sale/../tests/pos/tours/utils/feedback_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as EventTourUtils from "@pos_event/../tests/tours/utils/event_tour_utils";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("SellingEventInPos1", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("My Awesome Event"),
            EventTourUtils.increaseQuantityOfTicket("Ticket VIP"),
            EventTourUtils.increaseQuantityOfTicket("Ticket VIP"),
            Dialog.confirm(),
            EventTourUtils.answerGlobalQuestion("Text Box 1", "TB1-Answer"),
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

registry.category("web_tour.tours").add("SellingEventInPos2", {
    steps: () =>
        [
            Chrome.startPoS(),
            // Confirm popup - There isn't enough tickets available
            ProductScreen.clickDisplayedProduct("My Awesome Event"),
            EventTourUtils.increaseQuantityOfTicket("Ticket VIP"),
            EventTourUtils.increaseQuantityOfTicket("Ticket VIP"),
            Dialog.confirm(),
            Dialog.confirm(),
            ProductScreen.clickDisplayedProduct("Basic Event Ticket"),
            EventTourUtils.increaseQuantityOfTicket("Ticket Basic"),
            Dialog.confirm(),
            EventTourUtils.answerTicketQuestion("1", "Question1", "SHAG"),
            EventTourUtils.answerTicketQuestion("1", "Question2", "demo@test.com"),
            Dialog.confirm(),
            ProductScreen.longPressOrderline("Event Ticket"),
            EventTourUtils.answerTicketQuestion("1", "Question1", "DEMO"),
            Dialog.confirm(),
            ProductScreen.longPressOrderline("Event Ticket"),
            Dialog.confirm(),
            // Buy a VIP Ticket
            ProductScreen.clickDisplayedProduct("My Awesome Event"),
            EventTourUtils.increaseQuantityOfTicket("Ticket VIP"),
            Dialog.confirm(),
            EventTourUtils.answerTicketSelectQuestion("1", "Question1", "Q1-Answer1"),
            EventTourUtils.answerGlobalSelectQuestion("Question2", "Q2-Answer1"),
            Dialog.confirm(),
            Dialog.is({ title: "Oh snap !" }),
            Dialog.confirm("Ok"),
            EventTourUtils.answerGlobalSelectQuestion("Question3", "Q3-Answer1"),
            Dialog.confirm(),
            ProductScreen.totalAmountIs("300.00"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank", true, { remaining: "0.00" }),
            PaymentScreen.clickValidate(),
            FeedbackScreen.isShown(),
            FeedbackScreen.printTicket("Full Page"),
            FeedbackScreen.printTicket("Badge"),
            FeedbackScreen.clickNextOrder(),
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
