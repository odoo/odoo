/** @odoo-module */

import { ProductScreen } from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import { ReceiptScreen } from "@point_of_sale/../tests/tours/helpers/ReceiptScreenTourMethods";
import { PaymentScreen } from "@point_of_sale/../tests/tours/helpers/PaymentScreenTourMethods";
import { PartnerListScreen } from "@point_of_sale/../tests/tours/helpers/PartnerListScreenTourMethods";
import { TicketScreen } from "@point_of_sale/../tests/tours/helpers/TicketScreenTourMethods";
import { ErrorPopup } from "@point_of_sale/../tests/tours/helpers/ErrorPopupTourMethods";
import { Chrome } from "@point_of_sale/../tests/tours/helpers/ChromeTourMethods";
import { getSteps, startSteps } from "@point_of_sale/../tests/tours/helpers/utils";
import { registry } from "@web/core/registry";

startSteps();

ProductScreen.do.confirmOpeningPopup();
ProductScreen.do.clickHomeCategory();
Chrome.do.clickTicketButton();
TicketScreen.do.clickNewTicket();
ProductScreen.exec.addOrderline("Desk Pad", "1", "3");
Chrome.do.clickTicketButton();
TicketScreen.do.deleteOrder("-0002");
Chrome.do.confirmPopup();
TicketScreen.do.clickDiscard();
ProductScreen.check.orderIsEmpty();
ProductScreen.exec.addOrderline("Desk Pad", "1", "2");
Chrome.do.clickTicketButton();
TicketScreen.do.deleteOrder("-0001");
Chrome.do.confirmPopup();
TicketScreen.do.clickDiscard();
Chrome.do.clickTicketButton();
TicketScreen.check.nthRowContains(2, "-0003");
TicketScreen.do.clickDiscard();
ProductScreen.exec.addOrderline("Desk Pad", "1", "2");
ProductScreen.do.clickPartnerButton();
ProductScreen.do.clickCustomer("Nicole Ford");
Chrome.do.clickTicketButton();
TicketScreen.check.nthRowContains(2, "Nicole Ford");
TicketScreen.do.clickNewTicket();
ProductScreen.exec.addOrderline("Desk Pad", "1", "3");
ProductScreen.do.clickPartnerButton();
ProductScreen.do.clickCustomer("Brandon Freeman");
ProductScreen.do.clickPayButton();
PaymentScreen.check.isShown();
Chrome.do.clickTicketButton();
TicketScreen.check.nthRowContains(3, "Brandon Freeman");
TicketScreen.do.clickNewTicket();
ProductScreen.exec.addOrderline("Desk Pad", "2", "4");
ProductScreen.do.clickPayButton();
PaymentScreen.do.clickPaymentMethod("Bank");
PaymentScreen.do.clickValidate();
ReceiptScreen.check.isShown();
Chrome.do.clickTicketButton();
TicketScreen.check.nthRowContains(4, "Receipt");
TicketScreen.do.selectFilter("Receipt");
TicketScreen.check.nthRowContains(2, "Receipt");
TicketScreen.do.selectFilter("Payment");
TicketScreen.check.nthRowContains(2, "Payment");
TicketScreen.do.selectFilter("Ongoing");
TicketScreen.check.nthRowContains(2, "Ongoing");
TicketScreen.do.selectFilter("All active orders");
TicketScreen.check.nthRowContains(4, "Receipt");
TicketScreen.do.search("Customer", "Nicole");
TicketScreen.check.nthRowContains(2, "Nicole");
TicketScreen.do.search("Customer", "Brandon");
TicketScreen.check.nthRowContains(2, "Brandon");
TicketScreen.do.search("Receipt Number", "-0005");
TicketScreen.check.nthRowContains(2, "Receipt");
// Close the TicketScreen to see the current order which is in ReceiptScreen.
// This is just to remove the search string in the search bar.
TicketScreen.do.clickDiscard();
ReceiptScreen.check.isShown();
// Open again the TicketScreen to check the Paid filter.
Chrome.do.clickTicketButton();
TicketScreen.do.selectFilter("Paid");
TicketScreen.check.nthRowContains(2, "-0005");
// Pay the order that was in PaymentScreen.
TicketScreen.do.selectFilter("Payment");
TicketScreen.do.selectOrder("-0004");
PaymentScreen.do.clickPaymentMethod("Cash");
PaymentScreen.do.clickValidate();
ReceiptScreen.check.isShown();
ReceiptScreen.do.clickNextOrder();
ProductScreen.check.isShown();
// Check that the Paid filter will show the 2 synced orders.
Chrome.do.clickTicketButton();
TicketScreen.do.selectFilter("Paid");
TicketScreen.check.nthRowContains(2, "Brandon Freeman");
TicketScreen.check.nthRowContains(3, "-0005");
// Invoice order
TicketScreen.do.selectOrder("-0005");
TicketScreen.check.orderWidgetIsNotEmpty();
TicketScreen.do.clickControlButton("Invoice");
Chrome.do.confirmPopup();
PartnerListScreen.check.isShown();
PartnerListScreen.do.clickPartner("Colleen Diaz");
TicketScreen.check.partnerIs("Colleen Diaz");
// Reprint receipt
TicketScreen.do.clickControlButton("Print Receipt");
ReceiptScreen.check.isShown();
ReceiptScreen.do.clickBack();
// When going back, the ticket screen should be in its previous state.
TicketScreen.check.filterIs("Paid");

// Test refund //
TicketScreen.do.clickDiscard();
ProductScreen.check.isShown();
ProductScreen.check.orderIsEmpty();
ProductScreen.do.clickRefund();
// Filter should be automatically 'Paid'.
TicketScreen.check.filterIs("Paid");
TicketScreen.do.selectOrder("-0005");
TicketScreen.check.partnerIs("Colleen Diaz");
TicketScreen.do.clickOrderline("Desk Pad");
TicketScreen.do.pressNumpad("3");
// Error should show because 2 is more than the number
// that can be refunded.
ErrorPopup.do.clickConfirm();
TicketScreen.do.clickDiscard();
ProductScreen.check.isShown();
ProductScreen.check.orderIsEmpty();
ProductScreen.do.clickRefund();
TicketScreen.do.selectOrder("-0005");
TicketScreen.do.clickOrderline("Desk Pad");
TicketScreen.do.pressNumpad("1");
TicketScreen.check.toRefundTextContains("To Refund: 1.00");
TicketScreen.do.confirmRefund();
ProductScreen.check.isShown();
ProductScreen.check.selectedOrderlineHas("Desk Pad", "-1.00");
// Try changing the refund line to positive number.
// Error popup should show.
ProductScreen.do.pressNumpad("2");
ErrorPopup.do.clickConfirm();
// Change the refund line quantity to -3 -- not allowed
// so error popup.
ProductScreen.do.pressNumpad("+/- 3");
ErrorPopup.do.clickConfirm();
// Change the refund line quantity to -2 -- allowed.
ProductScreen.do.pressNumpad("+/- 2");
ProductScreen.check.selectedOrderlineHas("Desk Pad", "-2.00");
// Check if the amount being refunded changed to 2.
ProductScreen.do.clickRefund();
TicketScreen.do.selectOrder("-0005");
TicketScreen.check.toRefundTextContains("Refunding 2.00");
TicketScreen.do.clickDiscard();
// Pay the refund order.
ProductScreen.do.clickPayButton();
PaymentScreen.do.clickPaymentMethod("Bank");
PaymentScreen.do.clickValidate();
ReceiptScreen.check.isShown();
ReceiptScreen.do.clickNextOrder();
// Check refunded quantity.
ProductScreen.do.clickRefund();
TicketScreen.do.selectOrder("-0005");
TicketScreen.check.refundedNoteContains("2.00 Refunded");

registry.category("web_tour.tours").add("TicketScreenTour", { test: true, url: "/pos/ui", steps: getSteps() });
