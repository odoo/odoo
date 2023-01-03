/** @odoo-module */

import { PaymentScreen } from "@point_of_sale/../tests/tours/helpers/PaymentScreenTourMethods";
import { ReceiptScreen } from "@point_of_sale/../tests/tours/helpers/ReceiptScreenTourMethods";
import { Chrome } from "@pos_restaurant/../tests/tours/helpers/ChromeTourMethods";
import { FloorScreen } from "@pos_restaurant/../tests/tours/helpers/FloorScreenTourMethods";
import { ProductScreen } from "@pos_restaurant/../tests/tours/helpers/ProductScreenTourMethods";
import { TicketScreen } from "@point_of_sale/../tests/tours/helpers/TicketScreenTourMethods";
import { getSteps, startSteps } from "@point_of_sale/../tests/tours/helpers/utils";
import Tour from "web_tour.tour";

startSteps();

FloorScreen.do.clickTable("T5");

// Create first order
ProductScreen.do.confirmOpeningPopup();
ProductScreen.do.clickDisplayedProduct("Coca-Cola");
ProductScreen.check.selectedOrderlineHas("Coca-Cola");
ProductScreen.do.clickDisplayedProduct("Water");
ProductScreen.check.selectedOrderlineHas("Water");
ProductScreen.check.totalAmountIs("4.40");

// Create 2nd order (paid)
Chrome.do.clickTicketButton();
TicketScreen.do.clickNewTicket();
ProductScreen.do.clickDisplayedProduct("Coca-Cola");
ProductScreen.check.selectedOrderlineHas("Coca-Cola");
ProductScreen.do.clickDisplayedProduct("Minute Maid");
ProductScreen.check.selectedOrderlineHas("Minute Maid");
ProductScreen.check.totalAmountIs("4.40");
ProductScreen.do.clickPayButton();
PaymentScreen.do.clickPaymentMethod("Cash");
PaymentScreen.do.clickValidate();
ReceiptScreen.do.clickNextOrder();

// After clicking next order, floor screen is shown.
// It should have 1 as number of draft synced order.
FloorScreen.check.orderCountSyncedInTableIs("T5", "1");
FloorScreen.do.clickTable("T5");
ProductScreen.check.totalAmountIs("4.40");

// Create another draft order and go back to floor
Chrome.do.clickTicketButton();
TicketScreen.do.clickNewTicket();
ProductScreen.do.clickDisplayedProduct("Coca-Cola");
ProductScreen.check.selectedOrderlineHas("Coca-Cola");
ProductScreen.do.clickDisplayedProduct("Minute Maid");
ProductScreen.check.selectedOrderlineHas("Minute Maid");
Chrome.do.backToFloor();

// At floor screen, there should be 2 synced draft orders
FloorScreen.check.orderCountSyncedInTableIs("T5", "2");

// Delete the first order then go back to floor
FloorScreen.do.clickTable("T5");
ProductScreen.check.isShown();
Chrome.do.clickTicketButton();
TicketScreen.do.deleteOrder("-0001");
Chrome.do.confirmPopup();
TicketScreen.do.selectOrder("-0003");
Chrome.do.backToFloor();

// There should be 1 synced draft order.
FloorScreen.check.orderCountSyncedInTableIs("T5", "1");
Tour.register("pos_restaurant_sync", { test: true, url: "/pos/ui" }, getSteps());

startSteps();

/* pos_restaurant_sync_second_login
 *
 * This tour should be run after the first tour is done.
 */

// There is one draft synced order from the previous tour
FloorScreen.check.orderCountSyncedInTableIs("T5", "1");
FloorScreen.do.clickTable("T5");
ProductScreen.check.totalAmountIs("4.40");

// Test transfering an order
ProductScreen.do.clickTransferButton();
FloorScreen.do.clickTable("T4");

// Test if products still get merged after transfering the order
ProductScreen.do.clickDisplayedProduct("Coca-Cola");
ProductScreen.check.selectedOrderlineHas("Coca-Cola", "2.0");
ProductScreen.check.totalAmountIs("6.60");
ProductScreen.do.pressNumpad("1");
ProductScreen.check.totalAmountIs("4.40");
ProductScreen.do.clickPayButton();
PaymentScreen.do.clickPaymentMethod("Cash");
PaymentScreen.do.clickValidate();
ReceiptScreen.do.clickNextOrder();
// At this point, there are no draft orders.

FloorScreen.do.clickTable("T2");
ProductScreen.check.isShown();
ProductScreen.check.orderIsEmpty();
ProductScreen.do.clickTransferButton();
FloorScreen.do.clickTable("T4");
ProductScreen.do.clickDisplayedProduct("Coca-Cola");
ProductScreen.check.totalAmountIs("2.20");
Chrome.do.backToFloor();
FloorScreen.check.orderCountSyncedInTableIs("T4", "1");

Tour.register("pos_restaurant_sync_second_login", { test: true, url: "/pos/ui" }, getSteps());
