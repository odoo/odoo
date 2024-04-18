/** @odoo-module */

import * as BillScreen from "@pos_restaurant/../tests/tours/utils/bill_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/tours/utils/payment_screen_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import * as ReceiptScreen from "@point_of_sale/../tests/tours/utils/receipt_screen_util";
import * as Chrome from "@point_of_sale/../tests/tours/utils/chrome_util";
import * as FloorScreen from "@pos_restaurant/../tests/tours/utils/floor_screen_util";
import * as ProductScreenPos from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as ProductScreenResto from "@pos_restaurant/../tests/tours/utils/product_screen_util";
import * as Order from "@point_of_sale/../tests/tours/utils/generic_components/order_widget_util";
import * as TicketScreen from "@point_of_sale/../tests/tours/utils/ticket_screen_util";
import * as MergeTable from "@pos_restaurant/../tests/tours/utils/merge_table_util";
import { inLeftSide, negateStep } from "@point_of_sale/../tests/tours/utils/common";
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
function checkOrderChanges(expected_changes) {
    return [
        {
            content: `Check order changes with expected changes ${JSON.stringify(
                expected_changes
            )}`,
            trigger: ".pos", // dummy trigger
            run: function () {
                const orderChanges = window.posmodel.getOrderChanges();
                const orderChangesKeys = Object.keys(orderChanges.orderlines);
                const orderChangesNbr = orderChangesKeys.length;
                // Quick check for lenght
                if (expected_changes.length !== orderChangesNbr) {
                    console.error(
                        `Was expecting ${expected_changes.length} order changes, got ${orderChangesNbr}`
                    );
                }
                for (const expected_change of expected_changes) {
                    const order_change_line = orderChangesKeys.find((key) => {
                        const change = orderChanges.orderlines[key];
                        return (
                            change.name === expected_change.name &&
                            change.quantity === expected_change.quantity
                        );
                    });
                    if (order_change_line === undefined) {
                        console.error(
                            `Was expecting product "${expected_change.name}" with quantity ${
                                expected_change.quantity
                            } as order change, inside ${JSON.stringify(orderChanges.orderlines)}`
                        );
                    }
                }
            },
        },
    ];
}

registry.category("web_tour.tours").add("pos_restaurant_sync", {
    test: true,
    steps: () =>
        [
            Dialog.confirm("Open session"),

            // Create first order
            FloorScreen.clickTable("5"),
            ProductScreen.orderBtnIsPresent(),
            ProductScreen.clickDisplayedProduct("Coca-Cola", true),
            inLeftSide(Order.hasLine({ productName: "Coca-Cola", run: "dblclick" })),
            ProductScreen.clickDisplayedProduct("Water", true),
            ProductScreen.orderlineIsToOrder("Water"),
            ProductScreen.orderlineIsToSkip("Coca-Cola"),
            checkOrderChanges([{ name: "Water", quantity: 1 }]),
            ProductScreen.clickOrderButton(),
            {
                ...Dialog.confirm(),
                content:
                    "acknowledge printing error ( because we don't have printer in the test. )",
            },
            ProductScreen.orderlinesHaveNoChange(),
            checkOrderChanges([]),
            ProductScreen.totalAmountIs("4.40"),

            // Create 2nd order (paid)
            Chrome.clickMenuOption("Orders"),
            TicketScreen.clickNewTicket(),
            ProductScreen.clickDisplayedProduct("Coca-Cola", true),
            ProductScreen.clickDisplayedProduct("Minute Maid", true),
            ProductScreen.totalAmountIs("4.40"),
            checkOrderChanges([
                { name: "Coca-Cola", quantity: 1 },
                { name: "Minute Maid", quantity: 1 },
            ]),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            {
                ...Dialog.confirm(),
                content:
                    "acknowledge printing error ( because we don't have printer in the test. )",
            },
            ReceiptScreen.clickNextOrder(),

            // order on another table with a product variant
            FloorScreen.orderCountSyncedInTableIs("5", "1"),
            FloorScreen.clickTable("4"),
            ProductScreen.orderBtnIsPresent(),
            ProductScreen.clickDisplayedProduct("Desk Organizer", false),
            {
                ...Dialog.confirm(),
                content: "validate the variant dialog (with default values)",
            },
            ProductScreen.selectedOrderlineHas("Desk Organizer"),
            checkOrderChanges([{ name: "Desk Organizer (S, Leather)", quantity: 1 }]),
            ProductScreen.clickOrderButton(),
            {
                ...Dialog.confirm(),
                content:
                    "acknowledge printing error ( because we don't have printer in the test. )",
            },
            ProductScreen.orderlinesHaveNoChange(),
            checkOrderChanges([]),
            ProductScreen.totalAmountIs("5.87"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            // No "acknowledge printing error" this time as the printer order is already sent and no changes were made
            ReceiptScreen.clickNextOrder(),

            // After clicking next order, floor screen is shown.
            // It should have 1 as number of draft synced order.
            FloorScreen.orderCountSyncedInTableIs("5", "1"),
            FloorScreen.clickTable("5"),
            ProductScreen.totalAmountIs("4.40"),

            // Create another draft order and go back to floor
            Chrome.clickMenuOption("Orders"),
            TicketScreen.clickNewTicket(),
            ProductScreen.clickDisplayedProduct("Coca-Cola", true),
            ProductScreen.clickDisplayedProduct("Minute Maid", true),
            FloorScreen.backToFloor(),

            // At floor screen, there should be 2 synced draft orders
            FloorScreen.orderCountSyncedInTableIs("5", "2"),

            // Delete the first order then go back to floor
            FloorScreen.clickTable("5"),
            ProductScreen.isShown(),
            Chrome.clickMenuOption("Orders"),
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
            ProductScreen.isShown(),
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
    steps: () =>
        [
            // There is one draft synced order from the previous tour
            FloorScreen.clickTable("5"),
            ProductScreen.totalAmountIs("4.40"),

            // Test transfering an order
            ProductScreen.clickControlButtonMore(),
            ProductScreen.clickControlButton("Transfer"),
            FloorScreen.clickTable("4"),

            // Test if products still get merged after transfering the order
            ProductScreen.clickDisplayedProduct("Coca-Cola", true, "2.0"),
            ProductScreen.totalAmountIs("6.60"),
            ProductScreen.clickNumpad("1"),
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
            ProductScreen.clickControlButtonMore(),
            ProductScreen.clickControlButton("Transfer"),
            FloorScreen.clickTable("4"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.totalAmountIs("2.20"),
            FloorScreen.backToFloor(),
            FloorScreen.orderCountSyncedInTableIs("4", "1"),
        ].flat(),
});

registry.category("web_tour.tours").add("SaveLastPreparationChangesTour", {
    test: true,
    steps: () =>
        [
            Dialog.confirm("Open session"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Coca-Cola", true, "1.0"),
            ProductScreen.clickOrderButton(),
            ProductScreen.orderlinesHaveNoChange(),
            FloorScreen.backToFloor(),
        ].flat(),
});

const billScreenQRCode = {
    content: "QR codes are shown",
    trigger: ".pos-receipt #posqrcode",
    run: () => {},
};

registry.category("web_tour.tours").add("BillScreenTour", {
    test: true,
    steps: () =>
        [
            Dialog.confirm("Open session"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.clickControlButton("Bill"),
            // HACK: is_modal should be false so that the trigger can be found.
            { ...negateStep(billScreenQRCode), in_modal: false },
            BillScreen.closeBillPopup(),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            billScreenQRCode,
        ].flat(),
});

registry.category("web_tour.tours").add("MergeTableTour", {
    test: true,
    steps: () =>
        [
            Dialog.confirm("Open session"),
            ...MergeTable.mergeTableHelpers("5", "4"),
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
            ...MergeTable.checkMergeTableIsCancelHelpers(),
            ...MergeTable.mergeTableHelpers("5", "4"),
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
            ...MergeTable.checkMergeTableIsCancelHelpers(),
            ...MergeTable.mergeTableHelpers("5", "4"),
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
            ...MergeTable.checkMergeTableIsCancelHelpers(),
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
