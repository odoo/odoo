/** @odoo-module */

import * as BillScreen from "@pos_restaurant/../tests/tours/helpers/BillScreenTourMethods";
import * as PaymentScreen from "@point_of_sale/../tests/tours/helpers/PaymentScreenTourMethods";
import * as Dialog from "@point_of_sale/../tests/tours/helpers/DialogTourMethods";
import * as ReceiptScreen from "@point_of_sale/../tests/tours/helpers/ReceiptScreenTourMethods";
import * as Chrome from "@point_of_sale/../tests/tours/helpers/ChromeTourMethods";
import * as FloorScreen from "@pos_restaurant/../tests/tours/helpers/FloorScreenTourMethods";
import * as ProductScreenPos from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import * as ProductScreenResto from "@pos_restaurant/../tests/tours/helpers/ProductScreenTourMethods";
import * as Order from "@point_of_sale/../tests/tours/helpers/generic_components/OrderWidgetMethods";
import * as TicketScreen from "@point_of_sale/../tests/tours/helpers/TicketScreenTourMethods";
import { inLeftSide, negateStep } from "@point_of_sale/../tests/tours/helpers/utils";
import { registry } from "@web/core/registry";
import { TourError } from "@web_tour/tour_service/tour_utils";

const ProductScreen = { ...ProductScreenPos, ...ProductScreenResto };

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
            content: `Check last order preparation changes with expected changes ${JSON.stringify(
                expected_changes
            )}`,
            trigger: ".pos", // dummy trigger
            run: function () {
                const currentOrder = window.posmodel.get_order();
                const lastOrderPrepaChange = currentOrder.lastOrderPrepaChange;
                const lastOrderPrepaChangesObj = Object.values(lastOrderPrepaChange);
                // Quick check for lenght
                if (expected_changes.length !== lastOrderPrepaChangesObj.length) {
                    console.error(
                        `Was expecting ${expected_changes.length} order changes, got ${lastOrderPrepaChangesObj.length}`
                    );
                }
                for (let i = 0; i < expected_changes.length; i++) {
                    const expected_change = expected_changes[i];
                    const lastOrderPrepaChange = lastOrderPrepaChangesObj[i];
                    if (expected_change.name !== lastOrderPrepaChange.name) {
                        console.error(
                            `Was expecting ${expected_change.name} as name, got ${lastOrderPrepaChange.name}`
                        );
                    }
                    if (expected_change.quantity !== lastOrderPrepaChange.quantity) {
                        console.error(
                            `Was expecting ${expected_change.quantity} as quantity, got ${lastOrderPrepaChange.quantity}`
                        );
                    }
                }
            },
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
            ProductScreen.tableNameShown("5"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.selectedOrderlineHas("Coca-Cola"),
            inLeftSide(Order.hasLine({ productName: "Coca-Cola", run: "dblclick" })),
            ProductScreen.clickDisplayedProduct("Water"),
            ProductScreen.selectedOrderlineHas("Water"),
            ProductScreen.orderlineIsToOrder("Water"),
            ProductScreen.orderlineIsToSkip("Coca-Cola"),
            checkLastOrderPreparationChange([]), // No preparation changes for now
            ProductScreen.clickOrderButton(),
            {
                ...Dialog.confirm(),
                content:
                    "acknowledge printing error ( because we don't have printer in the test. )",
            },
            ProductScreen.orderlinesHaveNoChange(),
            checkLastOrderPreparationChange([{ name: "Water", quantity: 1 }]),
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
            {
                ...Dialog.confirm(),
                content:
                    "acknowledge printing error ( because we don't have printer in the test. )",
            },
            checkLastOrderPreparationChange([
                { name: "Coca-Cola", quantity: 1 },
                { name: "Minute Maid", quantity: 1 },
            ]),
            ReceiptScreen.clickNextOrder(),

            // order on another table with a product variant
            FloorScreen.orderCountSyncedInTableIs("5", "1"),
            FloorScreen.clickTable("4"),
            ProductScreen.orderBtnIsPresent(),
            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            {
                ...Dialog.confirm(),
                content: "validate the variant dialog (with default values)",
            },
            ProductScreen.selectedOrderlineHas("Desk Organizer"),
            ProductScreen.clickOrderButton(),
            {
                ...Dialog.confirm(),
                content:
                    "acknowledge printing error ( because we don't have printer in the test. )",
            },
            ProductScreen.orderlinesHaveNoChange(),
            checkLastOrderPreparationChange([{ name: "Desk Organizer (S, Leather)", quantity: 1 }]),
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
            Dialog.confirm(),
            {
                ...Dialog.confirm(),
                content:
                    "acknowledge printing error ( because we don't have printer in the test. )",
            },
            isSyncStatusConnected(),
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
            ProductScreen.controlButtonMore(),
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
            ProductScreen.controlButtonMore(),
            ProductScreen.controlButton("Transfer"),
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
    steps: () =>
        [
            Dialog.confirm("Open session"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.selectedOrderlineHas("Coca-Cola", "1.0"),
            ProductScreen.clickOrderButton(),
            ProductScreen.orderlinesHaveNoChange(),
        ].flat(),
});

registry.category("web_tour.tours").add("BillScreenTour", {
    test: true,
    steps: () =>
        [
            Dialog.confirm("Open session"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.controlButton("Bill"),
            negateStep(BillScreen.isQRCodeShown()),
            BillScreen.closeBillPopup(),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            BillScreen.isQRCodeShown(),
        ].flat(),
});

function mergeTableHelpers(childName, parentName) {
    return [
        FloorScreen.clickTable(childName),
        ProductScreen.controlButton("More"),
        ProductScreen.controlButton("Merge"),
        {
            content: `click the merge button`,
            trigger: 'i[aria-label="Merge"]',
        },
        FloorScreen.clickTable(parentName),
        FloorScreen.backToFloor(),
        {
            content: `Verify table ${childName} is merged into table ${parentName}`,
            trigger: `div.table div.label:contains("${parentName}")`,
            isCheck: true,
            run: () => {
                if ($(`div.table div.label:contains('${parentName}')`).length < 2) {
                    throw new TourError("Tables aren't merged");
                }
            },
        },
    ];
}

function checkMergeTableIsCancelHelpers() {
    return [
        {
            content: `Verify table 4 and 5 isn't merge anymore`,
            trigger: 'div.table div.label:contains("4")',
            isCheck: true,
            run: () => {
                if ($("div.table div.label:contains('4')").length !== 1) {
                    throw new TourError("Table is still merge");
                }
            },
        },
        {
            content: `Verify table 4 and 5 isn't merge anymore`,
            trigger: 'div.table div.label:contains("5")',
            isCheck: true,
            run: () => {
                if ($("div.table div.label:contains('5')").length !== 1) {
                    throw new TourError("Table is still merge");
                }
            },
        },
    ];
}

registry.category("web_tour.tours").add("MergeTableTour", {
    test: true,
    url: "/pos/ui",
    steps: () =>
        [
            Dialog.confirm("Open session"),
            ...mergeTableHelpers("5", "4"),
            FloorScreen.clickTable("4"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            {
                ...Dialog.confirm(),
                content:
                    "acknowledge printing error ( because we don't have printer in the test. )",
            },
            ReceiptScreen.clickNextOrder(),
            ...checkMergeTableIsCancelHelpers(),
            ...mergeTableHelpers("5", "4"),
            Chrome.clickMenuOption("Edit Plan"),
            {
                content: `select linked table`,
                trigger: 'div.isLinked div.label:contains("4")',
            },
            {
                content: `unlink in edit plan if unlink possible`,
                trigger: '.edit-buttons button:contains("Unlink")',
            },
            Chrome.clickMenuOption("Edit Plan"),
            ...checkMergeTableIsCancelHelpers(),
            ...mergeTableHelpers("5", "4"),
            {
                content: `refresh page`,
                trigger: 'div.table div.label:contains("4")',
                isCheck: true,
                run: () => {
                    window.location.reload();
                },
            },
            {
                content: `Verify table 4 and 5 is merge`,
                trigger: 'div.table div.label:contains("4")',
                isCheck: true,
                run: () => {
                    if ($("div.table div.label:contains('4')").length < 2) {
                        throw new TourError("Table isn't merge");
                    }
                },
            },
            Chrome.clickMenuOption("Edit Plan"),
            {
                content: `select linked table`,
                trigger: 'div.isLinked div.label:contains("4")',
            },
            {
                content: `unlink in edit plan if unlink possible`,
                trigger: '.edit-buttons button:contains("Unlink")',
            },
            Chrome.clickMenuOption("Edit Plan"),
            ...checkMergeTableIsCancelHelpers(),
            Chrome.clickMenuOption("Edit Plan"),
            FloorScreen.clickTable("4"),
            FloorScreen.ctrlClickTable("5"),
            {
                content: `link in edit plan if link possible`,
                trigger: '.edit-buttons button:contains("Link")',
            },
            Chrome.clickMenuOption("Edit Plan"),
            {
                content: `Verify table 4 and 5 is merge`,
                trigger: 'div.table div.label:contains("4")',
                isCheck: true,
                run: () => {
                    if ($("div.table div.label:contains('4')").length < 2) {
                        throw new TourError("Table isn't merge");
                    }
                },
            },
        ].flat(),
});

registry.category("web_tour.tours").add("CategLabelCheck", {
    test: true,
    steps: () =>
        [
            Dialog.confirm("Open session"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Test Multi Category Product"),
            ProductScreen.OrderButtonNotContain("Drinks"),
        ].flat(),
});
