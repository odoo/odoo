/** @odoo-module */

import { ProductScreen } from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import { FloorScreen } from "@pos_restaurant/../tests/tours/helpers/FloorScreenTourMethods";
import { TicketScreen } from "@point_of_sale/../tests/tours/helpers/TicketScreenTourMethods";
import { Chrome } from "@pos_restaurant/../tests/tours/helpers/ChromeTourMethods";
import { getSteps, startSteps } from "@point_of_sale/../tests/tours/helpers/utils";
import { registry } from "@web/core/registry";

startSteps();

ProductScreen.do.confirmOpeningPopup();
// New Ticket button should not be in the ticket screen if no table is selected.
Chrome.do.clickTicketButton();
TicketScreen.check.noNewTicketButton();
TicketScreen.do.clickDiscard();

// Deleting the last order in the table brings back to floorscreen
FloorScreen.do.clickTable("4");
ProductScreen.check.isShown();
Chrome.do.clickTicketButton();
TicketScreen.check.nthRowContains(2, "-0001");
TicketScreen.do.deleteOrder("-0001");
FloorScreen.check.isShown();

// Create 2 items in a table. From floorscreen, delete 1 item. Then select the other item.
// Correct order and screen should be displayed and the BackToFloorButton is shown.
FloorScreen.do.clickTable("2");
ProductScreen.exec.addOrderline("Minute Maid", "1", "2");
ProductScreen.check.totalAmountIs("2.0");
Chrome.do.clickTicketButton();
TicketScreen.do.clickNewTicket();
ProductScreen.exec.addOrderline("Coca-Cola", "2", "2");
ProductScreen.check.totalAmountIs("4.0");
Chrome.do.backToFloor();
FloorScreen.check.orderCountSyncedInTableIs("2", "2");
Chrome.do.clickTicketButton();
TicketScreen.do.deleteOrder("-0003");
Chrome.do.confirmPopup();
TicketScreen.do.selectOrder("-0002");
ProductScreen.check.isShown();
ProductScreen.check.totalAmountIs("2.0");
Chrome.check.backToFloorTextIs("Main Floor", "2");
Chrome.do.backToFloor();

// Make sure that order is deleted properly.
FloorScreen.do.clickTable("5");
ProductScreen.exec.addOrderline("Minute Maid", "1", "3");
ProductScreen.check.totalAmountIs("3.0");
Chrome.do.backToFloor();
FloorScreen.check.orderCountSyncedInTableIs("5", "1");
Chrome.do.clickTicketButton();
TicketScreen.do.deleteOrder("-0004");
Chrome.do.confirmPopup();
TicketScreen.do.clickDiscard();
FloorScreen.check.isShown();
FloorScreen.check.orderCountSyncedInTableIs("5", "0");
FloorScreen.do.clickTable("5");
ProductScreen.check.orderIsEmpty();

registry
    .category("web_tour.tours")
    .add("PosResTicketScreenTour", { test: true, url: "/pos/ui", steps: getSteps() });
