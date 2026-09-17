// Part of Odoo. See LICENSE file for full copyright and licensing details.
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as FeedbackScreen from "@point_of_sale/../tests/pos/tours/utils/feedback_screen_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as EventTourUtils from "@pos_event/../tests/tours/utils/event_tour_utils";
import { registry } from "@web/core/registry";

// The quotation has no attendee yet: the PoS asks for them.
registry.category("web_tour.tours").add("SettleEventQuotation", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            EventTourUtils.SettleEventRegistration(),
            Dialog.is({ title: "Tickets" }),
            EventTourUtils.answerTicketQuestion("1", "Name", "Attendee 1"),
            EventTourUtils.answerTicketQuestion("1", "Email", "attendee1@test.com"),
            EventTourUtils.answerTicketQuestion("1", "Phone", "+32456112233"),
            EventTourUtils.answerTicketQuestion("2", "Name", "Attendee 2"),
            EventTourUtils.answerTicketQuestion("2", "Email", "attendee2@test.com"),
            EventTourUtils.answerTicketQuestion("2", "Phone", "+32456112244"),
            Dialog.confirm("Confirm"),
            ProductScreen.totalAmountIs("200.00"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank", true, { remaining: "0.00" }),
            PaymentScreen.clickValidate(),
            FeedbackScreen.isShown(),
        ].flat(),
});

// The sale order registered its attendees already: settling asks for nothing.
registry.category("web_tour.tours").add("SettleRegisteredEventSaleOrder", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            EventTourUtils.SettleEventRegistration(),
            {
                content: "No attendee is asked for",
                trigger: "body:not(:has(.modal))",
            },
            ProductScreen.totalAmountIs("200.00"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank", true, { remaining: "0.00" }),
            PaymentScreen.clickValidate(),
            FeedbackScreen.isShown(),
        ].flat(),
});
