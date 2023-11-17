/** @odoo-module */

import * as PaymentScreen from "@point_of_sale/../tests/tours/helpers/PaymentScreenTourMethods";
import * as Dialog from "@point_of_sale/../tests/tours/helpers/DialogTourMethods";
import * as ReceiptScreen from "@point_of_sale/../tests/tours/helpers/ReceiptScreenTourMethods";
import * as Chrome from "@point_of_sale/../tests/tours/helpers/ChromeTourMethods";
import * as FloorScreen from "@pos_restaurant/../tests/tours/helpers/FloorScreenTourMethods";
import * as ProductScreenPos from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import * as ProductScreenResto from "@pos_restaurant/../tests/tours/helpers/ProductScreenTourMethods";
import * as Order from "@point_of_sale/../tests/tours/helpers/generic_components/OrderWidgetMethods";
import * as TicketScreen from "@point_of_sale/../tests/tours/helpers/TicketScreenTourMethods";
import { inLeftSide } from "@point_of_sale/../tests/tours/helpers/utils";
import { registry } from "@web/core/registry";

const ProductScreen = { ...ProductScreenPos, ...ProductScreenResto };
function isSyncStatusPending() {
    return [
        {
            trigger:
                ".pos-topheader .pos-rightheader .status-buttons .oe_status:has(.js_connecting)",
            run: () => {},
        },
    ];
}
function isSyncStatusConnected() {
    return [
        {
            trigger:
                ".pos-topheader .pos-rightheader .status-buttons .oe_status:has(.js_connected)",
            run: () => {},
        },
    ];
}
registry.category("web_tour.tours").add("pos_restaurant_sync", {
    test: true,
    url: "/pos/ui",
    steps: () =>
        [
            Dialog.confirm("Open session"),

            // Create first order
            FloorScreen.clickTable("5"),
            ProductScreen.orderBtnIsPresent(),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.selectedOrderlineHas("Coca-Cola"),
            inLeftSide(Order.hasLine({ productName: "Coca-Cola", run: "dblclick" })),
            ProductScreen.clickDisplayedProduct("Water"),
            ProductScreen.selectedOrderlineHas("Water"),
            ProductScreen.orderlineIsToOrder("Water"),
            ProductScreen.orderlineIsToSkip("Coca-Cola"),
            ProductScreen.clickOrderButton(),
            {
                ...Dialog.confirm(),
                content:
                    "acknowledge printing error ( because we don't have printer in the test. )",
            },
            ProductScreen.orderlinesHaveNoChange(),
            ProductScreen.totalAmountIs("4.40"),

            // Create 2nd order (paid)
            Chrome.clickMenuButton(),
            Chrome.clickTicketButton(),
            TicketScreen.clickNewTicket(),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.selectedOrderlineHas("Coca-Cola"),
            ProductScreen.clickDisplayedProduct("Minute Maid"),
            ProductScreen.selectedOrderlineHas("Minute Maid"),
            ProductScreen.totalAmountIs("4.40"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            {
                ...Dialog.confirm(),
                content:
                    "acknowledge printing error ( because we don't have printer in the test. )",
            },
            ReceiptScreen.clickNextOrder(),

            // After clicking next order, floor screen is shown.
            // It should have 1 as number of draft synced order.
            FloorScreen.orderCountSyncedInTableIs("5", "1"),
            FloorScreen.clickTable("5"),
            ProductScreen.totalAmountIs("4.40"),

            // Create another draft order and go back to floor
            Chrome.clickMenuButton(),
            Chrome.clickTicketButton(),
            TicketScreen.clickNewTicket(),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.selectedOrderlineHas("Coca-Cola"),
            ProductScreen.clickDisplayedProduct("Minute Maid"),
            ProductScreen.selectedOrderlineHas("Minute Maid"),
            FloorScreen.backToFloor(),

            // At floor screen, there should be 2 synced draft orders
            FloorScreen.orderCountSyncedInTableIs("5", "2"),

            // Delete the first order then go back to floor
            FloorScreen.clickTable("5"),
            ProductScreen.isShown(),
            Chrome.clickMenuButton(),
            Chrome.clickTicketButton(),
            TicketScreen.deleteOrder("-0001"),
            Dialog.confirm(),
            {
                ...Dialog.confirm(),
                ...isSyncStatusPending(),
                content:
                    "acknowledge printing error ( because we don't have printer in the test. )",
            },
            isSyncStatusConnected(),
            TicketScreen.selectOrder("-0003"),
            TicketScreen.loadSelectedOrder(),
            FloorScreen.backToFloor(),

            // There should be 1 synced draft order.
            FloorScreen.orderCountSyncedInTableIs("5", "2"),
        ].flat(),
});

/* pos_restaurant_sync_second_login
 *
 * This tour should be run after the first tour is done.
 */
registry.category("web_tour.tours").add("pos_restaurant_sync_second_login", {
    test: true,
    url: "/pos/ui",
    steps: () =>
        [
            // There is one draft synced order from the previous tour
            FloorScreen.clickTable("5"),
            ProductScreen.totalAmountIs("4.40"),

            // Test transfering an order
            ProductScreen.controlButton("Transfer"),
            FloorScreen.clickTable("4"),

            // Test if products still get merged after transfering the order
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.selectedOrderlineHas("Coca-Cola", "2.0"),
            ProductScreen.totalAmountIs("6.60"),
            ProductScreen.pressNumpad("1"),
            ProductScreen.totalAmountIs("4.40"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            {
                ...Dialog.confirm(),
                content:
                    "acknowledge printing error ( because we don't have printer in the test. )",
            },
            ReceiptScreen.clickNextOrder(),
            // At this point, there are no draft orders.

            FloorScreen.clickTable("2"),
            ProductScreen.isShown(),
            ProductScreen.orderIsEmpty(),
            ProductScreen.controlButton("Transfer"),
            FloorScreen.clickTable("4"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.totalAmountIs("2.20"),
            FloorScreen.backToFloor(),
            FloorScreen.orderCountSyncedInTableIs("4", "1"),
        ].flat(),
});
