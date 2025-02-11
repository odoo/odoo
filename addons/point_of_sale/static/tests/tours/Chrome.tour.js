/** @odoo-module */

import * as ProductScreen from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import * as ReceiptScreen from "@point_of_sale/../tests/tours/helpers/ReceiptScreenTourMethods";
import * as PaymentScreen from "@point_of_sale/../tests/tours/helpers/PaymentScreenTourMethods";
import * as TicketScreen from "@point_of_sale/../tests/tours/helpers/TicketScreenTourMethods";
import * as Chrome from "@point_of_sale/../tests/tours/helpers/ChromeTourMethods";
import * as Utils from "@point_of_sale/../tests/tours/helpers/utils";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("ChromeTour", {
    test: true,
    url: "/pos/ui",
    steps: () =>
        [
            ProductScreen.confirmOpeningPopup(),
            Chrome.clickMenuButton(),
            Chrome.isCashMoveButtonShown(),
            Chrome.clickMenuButton(),

            // Order 1 is at Product Screen
            ProductScreen.clickHomeCategory(),
            ProductScreen.addOrderline("Desk Pad", "1", "2", "2.0"),
            Chrome.clickMenuButton(),
            Chrome.clickTicketButton(),
            TicketScreen.checkStatus("-0001", "Ongoing"),

            // Order 2 is at Payment Screen
            TicketScreen.clickNewTicket(),
            ProductScreen.addOrderline("Monitor Stand", "3", "4", "12.0"),
            ProductScreen.clickPayButton(),
            PaymentScreen.isShown(),
            Chrome.clickMenuButton(),
            Chrome.clickTicketButton(),
            TicketScreen.checkStatus("-0002", "Payment"),

            // Order 3 is at Receipt Screen
            TicketScreen.clickNewTicket(),
            ProductScreen.addOrderline("Whiteboard Pen", "5", "6", "30.0"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.remainingIs("0.0"),
            PaymentScreen.validateButtonIsHighlighted(true),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            Chrome.clickMenuButton(),
            Chrome.clickTicketButton(),
            TicketScreen.checkStatus("-0003", "Receipt"),

            // Select order 1, should be at Product Screen
            TicketScreen.selectOrder("-0001"),
            TicketScreen.loadSelectedOrder(),
            ProductScreen.productIsDisplayed("Desk Pad"),
            ProductScreen.selectedOrderlineHas("Desk Pad", "1.0", "2.0"),

            // Select order 2, should be at Payment Screen
            Chrome.clickMenuButton(),
            Chrome.clickTicketButton(),
            TicketScreen.selectOrder("-0002"),
            TicketScreen.loadSelectedOrder(),
            PaymentScreen.emptyPaymentlines("12.0"),
            PaymentScreen.validateButtonIsHighlighted(false),

            // Select order 3, should be at Receipt Screen
            Chrome.clickMenuButton(),
            Chrome.clickTicketButton(),
            TicketScreen.selectOrder("-0003"),
            TicketScreen.loadSelectedOrder(),
            ReceiptScreen.totalAmountContains("30.0"),

            // Pay order 1, with change
            Chrome.clickMenuButton(),
            Chrome.clickTicketButton(),
            TicketScreen.selectOrder("-0001"),
            TicketScreen.loadSelectedOrder(),
            ProductScreen.isShown(),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.enterPaymentLineAmount("Cash", "20"),
            PaymentScreen.remainingIs("0.0"),
            PaymentScreen.validateButtonIsHighlighted(true),
            PaymentScreen.clickValidate(),
            ReceiptScreen.totalAmountContains("2.0"),

            // Order 1 now should have Receipt status
            Chrome.clickMenuButton(),
            Chrome.clickTicketButton(),
            TicketScreen.checkStatus("-0001", "Receipt"),

            // Select order 3, should still be at Receipt Screen
            // and the total amount doesn't change.
            TicketScreen.selectOrder("-0003"),
            TicketScreen.loadSelectedOrder(),
            ReceiptScreen.totalAmountContains("30.0"),

            // click next screen on order 3
            // then delete the new empty order
            ReceiptScreen.clickNextOrder(),
            ProductScreen.orderIsEmpty(),
            Chrome.clickMenuButton(),
            Chrome.clickTicketButton(),
            TicketScreen.deleteOrder("-0004"),
            TicketScreen.deleteOrder("-0001"),

            // After deleting order 1 above, order 2 became
            // the 2nd-row order and it has payment status
            TicketScreen.nthRowContains(2, "Payment"),
            TicketScreen.deleteOrder("-0002"),
            Chrome.confirmPopup(),
            TicketScreen.clickNewTicket(),

            // Invoice an order
            ProductScreen.addOrderline("Whiteboard Pen", "5", "6"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Partner Test 1"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickInvoiceButton(),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
        ].flat(),
});

registry.category("web_tour.tours").add("SearchMoreCustomer", {
    test: true,
    steps: () =>
        [
            ProductScreen.confirmOpeningPopup(),
            ProductScreen.clickPartnerButton(),
            ProductScreen.inputCustomerSearchbar("1111"),
            Utils.selectButton("Search more"),
            ProductScreen.clickCustomer("BPartner"),
            ProductScreen.isShown(),
        ].flat(),
});
