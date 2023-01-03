/** @odoo-module */

import { ProductScreen } from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import { ReceiptScreen } from "@point_of_sale/../tests/tours/helpers/ReceiptScreenTourMethods";
import { PaymentScreen } from "@point_of_sale/../tests/tours/helpers/PaymentScreenTourMethods";
import { TicketScreen } from "@point_of_sale/../tests/tours/helpers/TicketScreenTourMethods";
import { Chrome } from "@point_of_sale/../tests/tours/helpers/ChromeTourMethods";
import { getSteps, startSteps } from "@point_of_sale/../tests/tours/helpers/utils";
import Tour from "web_tour.tour";

startSteps();

// Order 1 is at Product Screen
ProductScreen.do.confirmOpeningPopup();
ProductScreen.do.clickHomeCategory();
ProductScreen.exec.addOrderline("Desk Pad", "1", "2", "2.0");
Chrome.do.clickTicketButton();
TicketScreen.check.checkStatus("-0001", "Ongoing");

// Order 2 is at Payment Screen
TicketScreen.do.clickNewTicket();
ProductScreen.exec.addOrderline("Monitor Stand", "3", "4", "12.0");
ProductScreen.do.clickPayButton();
PaymentScreen.check.isShown();
Chrome.do.clickTicketButton();
TicketScreen.check.checkStatus("-0002", "Payment");

// Order 3 is at Receipt Screen
TicketScreen.do.clickNewTicket();
ProductScreen.exec.addOrderline("Whiteboard Pen", "5", "6", "30.0");
ProductScreen.do.clickPayButton();
PaymentScreen.do.clickPaymentMethod("Bank");
PaymentScreen.check.remainingIs("0.0");
PaymentScreen.check.validateButtonIsHighlighted(true);
PaymentScreen.do.clickValidate();
ReceiptScreen.check.isShown();
Chrome.do.clickTicketButton();
TicketScreen.check.checkStatus("-0003", "Receipt");

// Select order 1, should be at Product Screen
TicketScreen.do.selectOrder("-0001");
ProductScreen.check.productIsDisplayed("Desk Pad");
ProductScreen.check.selectedOrderlineHas("Desk Pad", "1.0", "2.0");

// Select order 2, should be at Payment Screen
Chrome.do.clickTicketButton();
TicketScreen.do.selectOrder("-0002");
PaymentScreen.check.emptyPaymentlines("12.0");
PaymentScreen.check.validateButtonIsHighlighted(false);

// Select order 3, should be at Receipt Screen
Chrome.do.clickTicketButton();
TicketScreen.do.selectOrder("-0003");
ReceiptScreen.check.totalAmountContains("30.0");

// Pay order 1, with change
Chrome.do.clickTicketButton();
TicketScreen.do.selectOrder("-0001");
ProductScreen.check.isShown();
ProductScreen.do.clickPayButton();
PaymentScreen.do.clickPaymentMethod("Cash");
PaymentScreen.do.pressNumpad("2 0");
PaymentScreen.check.remainingIs("0.0");
PaymentScreen.check.validateButtonIsHighlighted(true);
PaymentScreen.do.clickValidate();
ReceiptScreen.check.totalAmountContains("2.0");

// Order 1 now should have Receipt status
Chrome.do.clickTicketButton();
TicketScreen.check.checkStatus("-0001", "Receipt");

// Select order 3, should still be at Receipt Screen
// and the total amount doesn't change.
TicketScreen.do.selectOrder("-0003");
ReceiptScreen.check.totalAmountContains("30.0");

// click next screen on order 3
// then delete the new empty order
ReceiptScreen.do.clickNextOrder();
ProductScreen.check.orderIsEmpty();
Chrome.do.clickTicketButton();
TicketScreen.do.deleteOrder("-0004");
TicketScreen.do.deleteOrder("-0001");

// After deleting order 1 above, order 2 became
// the 2nd-row order and it has payment status
TicketScreen.check.nthRowContains(2, "Payment");
TicketScreen.do.deleteOrder("-0002");
Chrome.do.confirmPopup();
TicketScreen.do.clickNewTicket();

// Invoice an order
ProductScreen.exec.addOrderline("Whiteboard Pen", "5", "6");
ProductScreen.do.clickPartnerButton();
ProductScreen.do.clickCustomer("Nicole Ford");
ProductScreen.do.clickPayButton();
PaymentScreen.do.clickPaymentMethod("Bank");
PaymentScreen.do.clickInvoiceButton();
PaymentScreen.do.clickValidate();
ReceiptScreen.check.isShown();

Tour.register("ChromeTour", { test: true, url: "/pos/ui" }, getSteps());
