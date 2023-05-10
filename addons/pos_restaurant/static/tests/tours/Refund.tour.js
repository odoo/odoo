/** @odoo-module */

import { ProductScreen } from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import { PaymentScreen } from "@point_of_sale/../tests/tours/helpers/PaymentScreenTourMethods";
import { ReceiptScreen } from "@point_of_sale/../tests/tours/helpers/ReceiptScreenTourMethods";
import { FloorScreen } from "@pos_restaurant/../tests/tours/helpers/FloorScreenTourMethods";
import { TicketScreen } from "@point_of_sale/../tests/tours/helpers/TicketScreenTourMethods";
import { getSteps, startSteps } from "@point_of_sale/../tests/tours/helpers/utils";
import Tour from "web_tour.tour";

// signal to start generating steps
// when finished, steps can be taken from getSteps
startSteps();

// Create first order and pay it
FloorScreen.do.clickTable("T2");
ProductScreen.do.confirmOpeningPopup();
ProductScreen.do.clickDisplayedProduct("Coca-Cola");
ProductScreen.check.selectedOrderlineHas("Coca-Cola");
ProductScreen.do.clickDisplayedProduct("Coca-Cola");
ProductScreen.check.selectedOrderlineHas("Coca-Cola");
ProductScreen.do.clickDisplayedProduct("Water");
ProductScreen.check.selectedOrderlineHas("Water");
ProductScreen.check.totalAmountIs("6.60");
ProductScreen.do.clickPayButton();
PaymentScreen.do.clickPaymentMethod("Cash");
PaymentScreen.do.clickValidate();
ReceiptScreen.do.clickNextOrder();

// Go to another table and refund one of the product
FloorScreen.do.clickTable("T4");
ProductScreen.check.orderIsEmpty();
ProductScreen.do.clickRefund();
TicketScreen.do.selectOrder("-0001");
TicketScreen.do.clickOrderline("Coca-Cola");
TicketScreen.do.pressNumpad("2");
TicketScreen.check.toRefundTextContains("To Refund: 2.00");
TicketScreen.do.confirmRefund();
ProductScreen.check.isShown();
ProductScreen.check.selectedOrderlineHas("Coca-Cola");
ProductScreen.check.totalAmountIs("-4.40");

Tour.register('RefundStayCurrentTableTour', { test: true, url: '/pos/ui' }, getSteps());

