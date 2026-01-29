/** @odoo-module */

import * as ProductScreenPos from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import * as ProductScreenResto from "@pos_restaurant/../tests/tours/helpers/ProductScreenTourMethods";
const ProductScreen = { ...ProductScreenPos, ...ProductScreenResto };
import * as FloorScreen from "@pos_restaurant/../tests/tours/helpers/FloorScreenTourMethods";
import * as TicketScreen from "@point_of_sale/../tests/tours/helpers/TicketScreenTourMethods";
import * as Chrome from "@point_of_sale/../tests/tours/helpers/ChromeTourMethods";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("PosResTicketScreenTour", {
    test: true,
    url: "/pos/ui",
    steps: () =>
        [
            ProductScreen.confirmOpeningPopup(),
            // New Ticket button should not be in the ticket screen if no table is selected.
            Chrome.clickMenuButton(),
            Chrome.clickTicketButton(),
            TicketScreen.noNewTicketButton(),
            TicketScreen.clickDiscard(),

            // Deleting the last order in the table brings back to floorscreen
            FloorScreen.clickTable("4"),
            ProductScreen.isShown(),
            Chrome.clickMenuButton(),
            Chrome.clickTicketButton(),
            TicketScreen.nthRowContains(2, "-0001"),
            TicketScreen.deleteOrder("-0001"),

            // Create 2 items in a table. From floorscreen, delete 1 item. Then select the other item.
            // Correct order and screen should be displayed and the BackToFloorButton is shown.
            FloorScreen.clickTable("2"),
            ProductScreen.addOrderline("Minute Maid", "1", "2"),
            ProductScreen.totalAmountIs("2.0"),
            Chrome.clickMenuButton(),
            Chrome.clickTicketButton(),
            TicketScreen.clickNewTicket(),
            ProductScreen.addOrderline("Coca-Cola", "2", "2"),
            ProductScreen.totalAmountIs("4.0"),
            FloorScreen.backToFloor(),
            FloorScreen.orderCountSyncedInTableIs("2", "3"),
            Chrome.clickMenuButton(),
            Chrome.clickTicketButton(),
            TicketScreen.deleteOrder("-0003"),
            Chrome.confirmPopup(),
            TicketScreen.doubleClickOrder("-0002"),
            ProductScreen.isShown(),
            ProductScreen.totalAmountIs("2.0"),
            FloorScreen.backToFloor(),

            // Make sure that order is deleted properly.
            FloorScreen.clickTable("5"),
            ProductScreen.addOrderline("Minute Maid", "1", "3"),
            ProductScreen.totalAmountIs("3.0"),
            FloorScreen.backToFloor(),
            FloorScreen.orderCountSyncedInTableIs("5", "1"),
            Chrome.clickMenuButton(),
            Chrome.clickTicketButton(),
            TicketScreen.deleteOrder("-0004"),
            Chrome.confirmPopup(),
            TicketScreen.clickDiscard(),
            FloorScreen.isShown(),
            FloorScreen.clickTable("5"),
            ProductScreen.orderIsEmpty(),
        ].flat(),
});

registry.category("web_tour.tours").add("OrderNumberConflictTour", {
    test: true,
    steps: () =>
        [
            FloorScreen.clickTable("3"),
            ProductScreen.isShown(),
            ProductScreen.addOrderline("Coca-Cola", "1", "3"),
            FloorScreen.backToFloor(),
            Chrome.clickMenuButton(),
            Chrome.clickTicketButton(),
            TicketScreen.nthColumnContains(2, 2, "Order"),
            TicketScreen.nthColumnContains(2, 3, "1"),
            TicketScreen.nthColumnContains(3, 2, "Self-Order"),
            TicketScreen.nthColumnContains(3, 3, "S"),
            TicketScreen.nthColumnContains(3, 3, "1")
        ].flat(),
});
