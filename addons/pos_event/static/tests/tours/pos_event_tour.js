// Part of Odoo. See LICENSE file for full copyright and licensing details.
import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as ReceiptScreen from "@point_of_sale/../tests/tours/utils/receipt_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/tours/utils/payment_screen_util";
import * as Chrome from "@point_of_sale/../tests/tours/utils/chrome_util";
import * as EventTourUtils from "@pos_event/../tests/tours/utils/event_tour_utils";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("SellingEventInPos", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            // Confirm popup - There isn't enough tickets available
            ProductScreen.clickDisplayedProduct("My Awesome Event"),
            EventTourUtils.increaseQuantityOfTicket("Ticket VIP"),
            EventTourUtils.increaseQuantityOfTicket("Ticket VIP"),
            Dialog.confirm(),
            Dialog.confirm(),

            // Buy a VIP Ticket
            ProductScreen.clickDisplayedProduct("My Awesome Event"),
            EventTourUtils.increaseQuantityOfTicket("Ticket VIP"),
            Dialog.confirm(),
            EventTourUtils.answerTicketSelectQuestion("1", "Question1", "Q1-Answer1"),
            EventTourUtils.answerGlobalSelectQuestion("Question2", "Q2-Answer1"),
            Dialog.confirm(),
            Dialog.is({ title: "Error" }),
            Dialog.confirm("Ok"),
            EventTourUtils.answerGlobalSelectQuestion("Question3", "Q3-Answer1"),
            Dialog.confirm(),
            ProductScreen.totalAmountIs("200.00"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank", true, { remaining: "0.00" }),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            EventTourUtils.printTicket("full"),
            EventTourUtils.printTicket("badge"),
            ReceiptScreen.clickNextOrder(),
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
            EventTourUtils.answerGlobalTextQuestion("Name", "Name 1"),
            EventTourUtils.answerGlobalTextQuestion("Email", "1@test.com"),
            Dialog.confirm(),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.clickNextOrder(),

            // Customer given, all information filled
            ProductScreen.clickDisplayedProduct("Event regitration not mandatory"),
            EventTourUtils.increaseQuantityOfTicket("Ticket Basic"),
            Dialog.confirm(),
            EventTourUtils.answerGlobalTextQuestion("Name", "Name 2"),
            EventTourUtils.answerGlobalTextQuestion("Email", "2@test.com"),
            Dialog.confirm(),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Event Parter"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.clickNextOrder(),

            // Customer given, partial information filled
            ProductScreen.clickDisplayedProduct("Event regitration not mandatory"),
            EventTourUtils.increaseQuantityOfTicket("Ticket Basic"),
            Dialog.confirm(),
            EventTourUtils.answerGlobalTextQuestion("Name", "Name 3"),
            Dialog.confirm(),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Event Parter"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.clickNextOrder(),

            // Customer given, partial information filled
            ProductScreen.clickDisplayedProduct("Event regitration not mandatory"),
            EventTourUtils.increaseQuantityOfTicket("Ticket Basic"),
            Dialog.confirm(),
            Dialog.confirm(),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Event Parter"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.clickNextOrder(),
        ].flat(),
});
