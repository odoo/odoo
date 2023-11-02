/** @odoo-module */

import { ProductScreen } from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import { ReceiptScreen } from "@point_of_sale/../tests/tours/helpers/ReceiptScreenTourMethods";
import { PaymentScreen } from "@point_of_sale/../tests/tours/helpers/PaymentScreenTourMethods";
import { NumberPopup } from "@point_of_sale/../tests/tours/helpers/NumberPopupTourMethods";
import { getSteps, startSteps } from "@point_of_sale/../tests/tours/helpers/utils";
import { registry } from "@web/core/registry";

startSteps();

// press close button in receipt screen
ProductScreen.exec.addOrderline("Letter Tray", "10", "5");
ProductScreen.check.selectedOrderlineHas("Letter Tray", "10");
ProductScreen.do.clickPayButton();
PaymentScreen.do.clickPaymentMethod("Bank");
PaymentScreen.check.validateButtonIsHighlighted(true);
PaymentScreen.do.clickValidate();
ReceiptScreen.check.receiptIsThere();
// letter tray has 10% tax (search SRC)
ReceiptScreen.check.totalAmountContains("55.0");
ReceiptScreen.do.clickNextOrder();

// send email in receipt screen
ProductScreen.do.clickHomeCategory();
ProductScreen.exec.addOrderline("Desk Pad", "6", "5", "30.0");
ProductScreen.exec.addOrderline("Whiteboard Pen", "6", "6", "36.0");
ProductScreen.exec.addOrderline("Monitor Stand", "6", "1", "6.0");
ProductScreen.do.clickPayButton();
PaymentScreen.do.clickPaymentMethod("Cash");
PaymentScreen.do.pressNumpad("7 0");
PaymentScreen.check.remainingIs("2.0");
PaymentScreen.do.pressNumpad("0");
PaymentScreen.check.remainingIs("0.00");
PaymentScreen.check.changeIs("628.0");
PaymentScreen.do.clickValidate();
ReceiptScreen.check.receiptIsThere();
ReceiptScreen.check.totalAmountContains("72.0");
ReceiptScreen.do.setEmail("test@receiptscreen.com");
ReceiptScreen.do.clickSend();
ReceiptScreen.check.emailIsSuccessful();
ReceiptScreen.do.clickNextOrder();

// order with tip
// check if tip amount is displayed
ProductScreen.exec.addOrderline("Desk Pad", "6", "5");
ProductScreen.do.clickPayButton();
PaymentScreen.do.clickTipButton();
NumberPopup.do.pressNumpad("1");
NumberPopup.check.inputShownIs("1");
NumberPopup.do.clickConfirm();
PaymentScreen.check.emptyPaymentlines("31.0");
PaymentScreen.do.clickPaymentMethod("Cash");
PaymentScreen.do.clickValidate();
ReceiptScreen.check.receiptIsThere();
ReceiptScreen.check.totalAmountContains("$ 30.00 + $ 1.00 tip");
ReceiptScreen.do.clickNextOrder();

// Test customer note in receipt
ProductScreen.exec.addOrderline("Desk Pad", "1", "5");
ProductScreen.exec.addCustomerNote("Test customer note");
ProductScreen.do.clickPayButton();
PaymentScreen.do.clickPaymentMethod("Bank");
PaymentScreen.do.clickValidate();
ReceiptScreen.check.customerNoteIsThere("Test customer note");

registry.category("web_tour.tours").add("ReceiptScreenTour", { test: true, url: "/pos/ui", steps: getSteps() });

startSteps();

ProductScreen.do.clickHomeCategory();
ProductScreen.exec.addOrderline('Test Product', '1');
ProductScreen.do.clickPricelistButton();
ProductScreen.do.selectPriceList('special_pricelist');
ProductScreen.check.discountOriginalPriceIs('7.0');
ProductScreen.do.clickPayButton();
PaymentScreen.do.clickPaymentMethod('Cash');
PaymentScreen.do.clickValidate();
ReceiptScreen.check.discountAmountIs('0.7');

registry.category("web_tour.tours").add("ReceiptScreenDiscountWithPricelistTour", { test: true, url: "/pos/ui", steps: getSteps() });

startSteps();

ProductScreen.do.clickHomeCategory();
ProductScreen.do.clickDisplayedProduct('Product A');
ProductScreen.do.enterLotNumber('123456789');
ProductScreen.do.clickPayButton();
PaymentScreen.do.clickPaymentMethod('Cash');
PaymentScreen.do.clickValidate();
ReceiptScreen.check.trackingMethodIsLot();

registry.category("web_tour.tours").add("ReceiptTrackingMethodTour", { test: true, url: "/pos/ui", steps: getSteps() });
