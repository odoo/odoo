/** @odoo-module */

import * as BillScreen from "@pos_restaurant/../tests/tours/helpers/BillScreenTourMethods";
import * as PaymentScreen from "@point_of_sale/../tests/tours/helpers/PaymentScreenTourMethods";
import * as ReceiptScreen from "@point_of_sale/../tests/tours/helpers/ReceiptScreenTourMethods";
import * as Chrome from "@point_of_sale/../tests/tours/helpers/ChromeTourMethods";
import * as FloorScreen from "@pos_restaurant/../tests/tours/helpers/FloorScreenTourMethods";
import * as ProductConfigurator from "@point_of_sale/../tests/tours/helpers/ProductConfiguratorTourMethods";
import * as ProductScreenPos from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import * as ProductScreenResto from "@pos_restaurant/../tests/tours/helpers/ProductScreenTourMethods";
import * as Order from "@point_of_sale/../tests/tours/helpers/generic_components/OrderWidgetMethods";
import * as TicketScreen from "@point_of_sale/../tests/tours/helpers/TicketScreenTourMethods";
import { inLeftSide, negateStep } from "@point_of_sale/../tests/tours/helpers/utils";
import { registry } from "@web/core/registry";

const ProductScreen = { ...ProductScreenPos, ...ProductScreenResto };
function isSyncStatusPending() {
    return [
        {
            trigger: ".pos-topheader .pos-rightheader .status-buttons .oe_status:has(.js_msg)",
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
function checkLastOrderPreparationChange(expected_changes) {
    return [
        {
            content: `Check last order preparation changes with expected changes ${JSON.stringify(expected_changes)}`,
            trigger: ".pos", // dummy trigger
            run: function() {
                const currentOrder = window.posmodel.get_order();
                const lastOrderPrepaChange = currentOrder.lastOrderPrepaChange;
                const lastOrderPrepaChangesObj = Object.values(lastOrderPrepaChange);
                
                // Quick check for lenght
                if (expected_changes.length !== lastOrderPrepaChangesObj.length) {
                    console.error(`Was expecting ${expected_changes.length} order changes, got ${lastOrderPrepaChangesObj.length}`);
                }
                
                for (let i = 0; i < expected_changes.length; i++) {
                    const expected_change = expected_changes[i];
                    const lastOrderPrepaChange = lastOrderPrepaChangesObj[i];
                    if (expected_change.name !== lastOrderPrepaChange.name) {
                        console.error(`Was expecting ${expected_change.name} as name, got ${lastOrderPrepaChange.name}`);
                    }
                    if (expected_change.quantity !== lastOrderPrepaChange.quantity) {
                        console.error(`Was expecting ${expected_change.quantity} as quantity, got ${lastOrderPrepaChange.quantity}`);
                    }
                }
            }
        },
    ];
}

registry.category("web_tour.tours").add("pos_restaurant_sync", {
    test: true,
    url: "/pos/ui",
    steps: () =>
        [
            ProductScreen.confirmOpeningPopup(),

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
            checkLastOrderPreparationChange([]), // No preparation changes for now
            ProductScreen.clickOrderButton(),
            ProductScreen.isPrintingError(),
            ProductScreen.orderlinesHaveNoChange(),
            checkLastOrderPreparationChange([{"name": "Water", "quantity": 1}]),
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

            // When reaching the receipt screen, the order is sent for printing.
            ProductScreen.isPrintingError(),
            checkLastOrderPreparationChange([
                {"name": "Coca-Cola", "quantity": 1},
                {"name": "Minute Maid", "quantity": 1}
            ]),
            ReceiptScreen.clickNextOrder(),

            // order on another table with a product variant
            FloorScreen.orderCountSyncedInTableIs("5", "1"),
            FloorScreen.clickTable("4"),
            ProductScreen.orderBtnIsPresent(),
            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            ProductConfigurator.isShown(),
            ProductConfigurator.confirmAttributes(),
            ProductScreen.selectedOrderlineHas("Desk Organizer"),
            ProductScreen.clickOrderButton(),
            ProductScreen.isPrintingError(),
            ProductScreen.orderlinesHaveNoChange(),
            checkLastOrderPreparationChange([
                {"name": "Desk Organizer (S, Leather)", "quantity": 1}
            ]),
            ProductScreen.totalAmountIs("5.87"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
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
            Chrome.confirmPopup(),
            isSyncStatusPending(),
            isSyncStatusConnected(),

            // When deleting an order, the unprinted changes will be sent for printing.
            ProductScreen.isPrintingError(),

            TicketScreen.selectOrder("-0004"),
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
            ProductScreen.clickTransferButton(),
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
            ReceiptScreen.clickNextOrder(),
            // At this point, there are no draft orders.

            FloorScreen.clickTable("2"),
            ProductScreen.isShown(),
            ProductScreen.orderIsEmpty(),
            ProductScreen.clickTransferButton(),
            FloorScreen.clickTable("4"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.totalAmountIs("2.20"),
            FloorScreen.backToFloor(),
            FloorScreen.orderCountSyncedInTableIs("4", "1"),
        ].flat(),
});

registry.category("web_tour.tours").add("SaveLastPreparationChangesTour", {
        test: true,
        url: "/pos/ui",
        steps: () => [
            ProductScreen.confirmOpeningPopup(),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.selectedOrderlineHas("Coca-Cola", "1.0"),
            ProductScreen.clickOrderButton(),
            ProductScreen.orderlinesHaveNoChange()
        ].flat(),
    });

registry.category("web_tour.tours").add("BillScreenTour", {
    test: true,
    steps: () => [
        ProductScreen.confirmOpeningPopup(),
        FloorScreen.clickTable("5"),
        ProductScreen.clickDisplayedProduct("Coca-Cola"),
        BillScreen.clickBillButton(),
        negateStep(BillScreen.isQRCodeShown()),
        BillScreen.clickOk(),
        ProductScreen.clickPayButton(),
        PaymentScreen.clickPaymentMethod("Bank"),
        PaymentScreen.clickValidate(),
        BillScreen.isQRCodeShown(),
    ].flat(),
});
