/** @odoo-module */

import { Chrome } from "@point_of_sale/../tests/tours/helpers/ChromeTourMethods";
import { PaymentScreen } from "@point_of_sale/../tests/tours/helpers/PaymentScreenTourMethods";
import { ProductScreen } from "@pos_sale/../tests/helpers/ProductScreenTourMethods";
import { ReceiptScreen } from "@point_of_sale/../tests/tours/helpers/ReceiptScreenTourMethods";
import { TicketScreen } from "@point_of_sale/../tests/tours/helpers/TicketScreenTourMethods";
import { getSteps, startSteps } from "@point_of_sale/../tests/tours/helpers/utils";
import Tour from "web_tour.tour";

// signal to start generating steps
// when finished, steps can be taken from getSteps
startSteps();

ProductScreen.do.confirmOpeningPopup();
ProductScreen.do.clickQuotationButton();
ProductScreen.do.selectFirstOrder();
ProductScreen.check.selectedOrderlineHas('Pizza Chicken', 9);
ProductScreen.do.pressNumpad('Qty 2'); // Change the quantity of the product to 2
ProductScreen.check.selectedOrderlineHas('Pizza Chicken', 2);
ProductScreen.do.clickPayButton();
PaymentScreen.do.clickPaymentMethod('Bank');
PaymentScreen.do.clickValidate();
Chrome.do.clickTicketButton();

Tour.register('PosSettleOrder', { test: true, url: '/pos/ui' }, getSteps());

startSteps();

ProductScreen.do.confirmOpeningPopup();
ProductScreen.do.clickQuotationButton();
// The second item in the list is the first sale.order.
ProductScreen.do.selectNthOrder(2);
ProductScreen.check.selectedOrderlineHas('product1', 1);
ProductScreen.check.totalAmountIs("10.00");

ProductScreen.do.clickQuotationButton();
// The first item in the list is the second sale.order.
// Selecting the 2nd sale.order should use a new order,
// therefore, the total amount will change.
ProductScreen.do.selectNthOrder(1);
ProductScreen.check.selectedOrderlineHas('product2', 1);
ProductScreen.check.totalAmountIs("11.00");

Tour.register('PosSettleOrderIncompatiblePartner', { test: true, url: '/pos/ui' }, getSteps());

startSteps();

ProductScreen.do.confirmOpeningPopup();
ProductScreen.do.clickQuotationButton();
ProductScreen.do.selectFirstOrder();
ProductScreen.do.clickOrderline("Product A", "1");
ProductScreen.check.selectedOrderlineHas('Product A', '1.00');
ProductScreen.do.clickOrderline("Product B", "1");
ProductScreen.do.pressNumpad('Qty 0');
ProductScreen.check.selectedOrderlineHas('Product B', '0.00');
ProductScreen.do.clickPayButton();
PaymentScreen.do.clickPaymentMethod('Bank');
PaymentScreen.check.remainingIs('0.0');
PaymentScreen.do.clickValidate();
ReceiptScreen.check.isShown();

Tour.register('PosSettleOrder2', { test: true, url: '/pos/ui' }, getSteps());

startSteps();

ProductScreen.do.clickQuotationButton();
ProductScreen.do.downPaymentFirstOrder();
ProductScreen.do.clickPayButton();
PaymentScreen.do.clickPaymentMethod('Cash');
PaymentScreen.do.clickValidate();
ReceiptScreen.do.clickNextOrder();
ProductScreen.do.clickRefund();
// Filter should be automatically 'Paid'.
TicketScreen.check.filterIs('Paid');
TicketScreen.do.selectOrder('-0001');
TicketScreen.do.clickOrderline('Down Payment');
TicketScreen.do.pressNumpad('1');
TicketScreen.do.confirmRefund();
ProductScreen.do.clickPayButton();
PaymentScreen.do.clickPaymentMethod('Cash');
PaymentScreen.do.clickValidate();
ReceiptScreen.do.clickNextOrder();

Tour.register('PosRefundDownpayment', { test: true, url: '/pos/ui' }, getSteps());
