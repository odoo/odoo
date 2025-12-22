/* global posmodel */

import * as BillScreen from "@pos_restaurant/../tests/tours/utils/bill_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/tours/utils/payment_screen_util";
import * as combo from "@point_of_sale/../tests/tours/utils/combo_popup_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import * as ReceiptScreen from "@point_of_sale/../tests/tours/utils/receipt_screen_util";
import * as ChromePos from "@point_of_sale/../tests/tours/utils/chrome_util";
import * as ChromeRestaurant from "@pos_restaurant/../tests/tours/utils/chrome";
const Chrome = { ...ChromePos, ...ChromeRestaurant };
import * as FloorScreen from "@pos_restaurant/../tests/tours/utils/floor_screen_util";
import * as ProductScreenPos from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as ProductScreenResto from "@pos_restaurant/../tests/tours/utils/product_screen_util";
import * as Order from "@point_of_sale/../tests/tours/utils/generic_components/order_widget_util";
import * as TicketScreen from "@point_of_sale/../tests/tours/utils/ticket_screen_util";
import {
    inLeftSide,
    negateStep,
    waitForLoading,
    refresh,
} from "@point_of_sale/../tests/tours/utils/common";
import { registry } from "@web/core/registry";
import * as Numpad from "@point_of_sale/../tests/tours/utils/numpad_util";
import { delay } from "@odoo/hoot-dom";
import * as TextInputPopup from "@point_of_sale/../tests/tours/utils/text_input_popup_util";

const ProductScreen = { ...ProductScreenPos, ...ProductScreenResto };

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
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            // Create a floating order. The idea is to have one of the draft orders be a floating order during the tour.
            Chrome.createFloatingOrder(),

            // Dine in / Takeaway can be toggled.
            ProductScreen.clickControlButton("Switch to Takeaway"),
            ProductScreen.clickControlButton("Switch to Dine in"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            Chrome.clickPlanButton(),
            // Check if there is no active Order
            Chrome.activeTableOrOrderIs("Table"),

            // Create first order
            FloorScreen.clickTable("5"),
            ProductScreen.orderBtnIsPresent(),
            Chrome.isTabActive("5"),
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
            Chrome.clickPlanButton(),
            FloorScreen.clickTable("2"),
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
            ReceiptScreen.clickNextOrder(),
            // Check if there ids no active Order
            Chrome.activeTableOrOrderIs("Table"),

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
            checkOrderChanges([{ name: "Desk Organizer (Leather, S)", quantity: 1 }]),
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
            Chrome.clickPlanButton(),
            FloorScreen.clickTable("2"),
            ProductScreen.clickDisplayedProduct("Coca-Cola", true),
            ProductScreen.clickDisplayedProduct("Minute Maid", true),
            Chrome.clickPlanButton(),
            FloorScreen.orderCountSyncedInTableIs("5", "1"),

            // Delete the first order then go back to floor
            Chrome.clickMenuOption("Orders"),
            // The order ref ends with -0002 because it is actually the 2nd order made in the session.
            // The first order made in the session is a floating order.
            TicketScreen.deleteOrder("Main Floor/2"),
            Dialog.confirm(),
            Chrome.isSyncStatusConnected(),
            TicketScreen.selectOrder("Main Floor/5"),
            TicketScreen.loadSelectedOrder(),
            ProductScreen.isShown(),
            Chrome.clickPlanButton(),

            // There should be 0 synced draft order as we already deleted -0002.
            FloorScreen.clickTable("2"),
            ProductScreen.orderIsEmpty(),
        ].flat(),
});

/* pos_restaurant_sync_second_login
 *
 * This tour should be run after the first tour is done.
 */
registry.category("web_tour.tours").add("pos_restaurant_sync_second_login", {
    steps: () =>
        [
            // There is one draft synced order from the previous tour
            Chrome.startPoS(),
            FloorScreen.clickTable("5"),
            ProductScreen.totalAmountIs("4.40"),

            // Test transfering an order
            ProductScreen.clickControlButton("Transfer"),
            {
                trigger: ".table:contains(4)",
                async run(helpers) {
                    await delay(500);
                    await helpers.click();
                },
            },
            Chrome.activeTableOrOrderIs("4"),

            // Test if products still get merged after transfering the order
            ProductScreen.totalAmountIs("4.40"),
            ProductScreen.clickDisplayedProduct("Water"),
            ProductScreen.totalAmountIs("6.60"),
            ProductScreen.clickNumpad("1"),
            ProductScreen.totalAmountIs("4.40"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.clickNextOrder(),
            // At this point, there are no draft orders.

            {
                trigger: ".table:contains(2)",
                async run(helpers) {
                    await delay(500);
                    await helpers.click();
                },
            },
            Chrome.activeTableOrOrderIs("2"),
            ProductScreen.isShown(),
            ProductScreen.orderIsEmpty(),
            ProductScreen.clickControlButton("Transfer"),
            {
                trigger: ".table:contains(4)",
                async run(helpers) {
                    await delay(500);
                    await helpers.click();
                },
            },
            Chrome.activeTableOrOrderIs("4"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.totalAmountIs("2.20"),
            Chrome.clickPlanButton(),
            FloorScreen.orderCountSyncedInTableIs("4", "1"),
        ].flat(),
});

registry.category("web_tour.tours").add("SaveLastPreparationChangesTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Coca-Cola", true, "1.0"),
            ProductScreen.orderlineIsToOrder("Coca-Cola"),
            ProductScreen.clickOrderButton(),
            Chrome.waitRequest(),
            ProductScreen.orderlinesHaveNoChange(),
            Order.hasLine({
                productName: "Coca-Cola",
                quantity: 1,
                withClass: ":eq(0)",
            }),
            Chrome.clickPlanButton(),
            FloorScreen.hasTable("2"),
            FloorScreen.hasTable("4"),
            FloorScreen.hasTable("5"),
        ].flat(),
});

const billScreenQRCodeData = [
    {
        content: "Unique code is shown",
        trigger: ".pos-receipt .unique-code",
    },
    {
        content: "Portal url is shown",
        trigger: ".pos-receipt .portal-url",
    },
];

registry.category("web_tour.tours").add("BillScreenTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.clickControlButton("Bill"),
            // HACK: is_modal should be false so that the trigger can be found.
            billScreenQRCodeData.map(negateStep),
            BillScreen.closeBillPopup(),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            ...billScreenQRCodeData,
        ].flat(),
});

registry.category("web_tour.tours").add("OrderTrackingTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.clickDisplayedProduct("Coca-Cola", true, "2.0"),
            Chrome.clickPlanButton(),
            FloorScreen.clickTable("5"),
            inLeftSide([
                ...ProductScreen.clickLine("Coca-Cola", "2.0"),
                ...ProductScreen.selectedOrderlineHasDirect("Coca-Cola", "2.0"),
                ...["⌫", "1"].map(Numpad.click),
                ...ProductScreen.selectedOrderlineHasDirect("Coca-Cola", "1.0"),
            ]),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
        ].flat(),
});
registry.category("web_tour.tours").add("CategLabelCheck", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Test Multi Category Product"),
            ProductScreen.OrderButtonNotContain("Drinks"),
        ].flat(),
});
registry.category("web_tour.tours").add("OrderChange", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Coca-Cola", true, "1.0"),
            ProductScreen.clickOrderButton(),
            {
                ...Dialog.confirm(),
                content:
                    "acknowledge printing error ( because we don't have printer in the test. )",
            },
            ProductScreen.orderlinesHaveNoChange(),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickNumpad("+10"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            TicketScreen.receiptChangeIs("7.80"),
        ].flat(),
});

registry.category("web_tour.tours").add("CrmTeamTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            Chrome.clickPlanButton(),
            FloorScreen.clickTable("5"),
            Chrome.clickPlanButton(),
        ].flat(),
});

registry.category("web_tour.tours").add("PoSPaymentSyncTour1", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.totalAmountIs("2.20"),
            ProductScreen.clickPayButton(),
            PaymentScreen.emptyPaymentlines("2.20"),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickBackToProductScreen(),
            ProductScreen.isShown(),
            ProductScreen.clickOrderButton(),
            ProductScreen.orderlinesHaveNoChange(),
            Chrome.clickPlanButton(),
        ].flat(),
});

registry.category("web_tour.tours").add("PoSPaymentSyncTour2", {
    steps: () =>
        [
            Chrome.startPoS(),
            FloorScreen.clickTable("5"),
            PaymentScreen.isShown(),
            PaymentScreen.clickBackToProductScreen(),
            ProductScreen.isShown(),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.totalAmountIs("4.40"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentlineDelButton("Bank", "2.20"),
            PaymentScreen.emptyPaymentlines("4.40"),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickBackToProductScreen(),
            ProductScreen.isShown(),
            ProductScreen.clickOrderButton(),
            ProductScreen.orderlinesHaveNoChange(),
            Chrome.clickPlanButton(),
        ].flat(),
});

registry.category("web_tour.tours").add("PoSPaymentSyncTour3", {
    steps: () =>
        [
            Chrome.startPoS(),
            FloorScreen.clickTable("5"),
            PaymentScreen.isShown(),
            PaymentScreen.clickBackToProductScreen(),
            ProductScreen.isShown(),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.totalAmountIs("6.60"),
            ProductScreen.clickPayButton(),
            PaymentScreen.remainingIs("2.2"),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickBackToProductScreen(),
            ProductScreen.isShown(),
            ProductScreen.clickOrderButton(),
            ProductScreen.orderlinesHaveNoChange(),
            Chrome.clickPlanButton(),
        ].flat(),
});

registry.category("web_tour.tours").add("PreparationPrinterContent", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Product Test"),
            Chrome.freezeDateTime(1739370000000),
            Dialog.confirm("Add"),
            ProductScreen.totalAmountIs("10"),
            {
                content: "Check if order preparation contains always Variant",
                trigger: "body",
                run: async () => {
                    const order = posmodel.get_order();
                    const data = posmodel.getOrderChanges();
                    const changes = Object.values(data.orderlines);
                    const printed = await posmodel.getRenderedReceipt(order, "New", changes);

                    if (!printed.innerHTML.includes("Product Test (Value 1)")) {
                        throw new Error("Product Test (Value 1) not found in printed receipt");
                    }
                    const receiptHeader = printed.querySelector(".receipt-header");
                    if (!receiptHeader.innerHTML.includes("14:20")) {
                        throw new Error(
                            "Expected timestamp '14:20' not found in the printed receipt header"
                        );
                    }
                },
            },
        ].flat(),
});

registry.category("web_tour.tours").add("ComboSortedPreparationReceiptTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Office Combo"),
            combo.select("Combo Product 2"),
            combo.select("Combo Product 4"),
            combo.select("Combo Product 6"),
            Dialog.confirm(),
            ProductScreen.clickDisplayedProduct("Office Combo"),
            combo.select("Combo Product 1"),
            combo.select("Combo Product 5"),
            combo.select("Combo Product 8"),
            Dialog.confirm(),
            {
                content: "Check if order preparation has product correctly ordered",
                trigger: "body",
                run: async () => {
                    const order = posmodel.get_order();
                    const data = posmodel.getOrderChanges();
                    const changes = Object.values(data.orderlines);
                    const printed = await posmodel.getRenderedReceipt(order, "New", changes);
                    const orderLines = [...printed.querySelectorAll(".orderline")];
                    const orderLinesInnerText = orderLines.map((orderLine) => orderLine.innerText);
                    const expectedOrderLines = [
                        "Office Combo",
                        "Combo Product 2",
                        "Combo Product 4",
                        "Combo Product 6",
                        "Office Combo",
                        "Combo Product 1",
                        "Combo Product 5",
                        "Combo Product 8",
                    ];
                    for (let i = 0; i < orderLinesInnerText.length; i++) {
                        if (!orderLinesInnerText[i].includes(expectedOrderLines[i])) {
                            throw new Error("Order line mismatch");
                        }
                    }
                },
            },
            ProductScreen.totalAmountIs("95.00"),
            ProductScreen.clickPayButton(),
        ].flat(),
});

registry.category("web_tour.tours").add("TableTransferPreparationChange1", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            //Transfer sent product on table with same product sent
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Product Test"),
            ProductScreen.clickOrderButton(),
            Dialog.confirm(),
            ProductScreen.orderlinesHaveNoChange("Product Test"),
            Chrome.clickPlanButton(),
            FloorScreen.clickTable("4"),
            ProductScreen.clickDisplayedProduct("Product Test"),
            ProductScreen.clickOrderButton(),
            Dialog.confirm(),
            ProductScreen.orderlinesHaveNoChange("Product Test"),
            ProductScreen.clickControlButton("Transfer"),
            FloorScreen.clickTable("5"),
            ProductScreen.orderlinesHaveNoChange("Product Test"),
            ProductScreen.orderLineHas("Product Test", "2"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
        ].flat(),
});

registry.category("web_tour.tours").add("TableTransferPreparationChange2", {
    steps: () =>
        [
            Chrome.startPoS(),
            //Transfer sent product on table with same product not sent
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Product Test"),
            ProductScreen.orderlineIsToOrder("Product Test"),
            Chrome.clickPlanButton(),
            FloorScreen.clickTable("4"),
            ProductScreen.clickDisplayedProduct("Product Test"),
            ProductScreen.clickOrderButton(),
            Dialog.confirm(),
            ProductScreen.orderlinesHaveNoChange("Product Test"),
            ProductScreen.clickControlButton("Transfer"),
            FloorScreen.clickTable("5"),
            ProductScreen.orderlineIsToOrder("Product Test"),
            ProductScreen.orderLineHas("Product Test", "2"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            Chrome.clickPlanButton(),
        ].flat(),
});

registry.category("web_tour.tours").add("TableTransferPreparationChange3", {
    steps: () =>
        [
            Chrome.startPoS(),
            //Transfer sent product on table without the same product
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Product Test"),
            ProductScreen.clickOrderButton(),
            Dialog.confirm(),
            ProductScreen.clickControlButton("Transfer"),
            FloorScreen.clickTable("4"),
            ProductScreen.orderlinesHaveNoChange("Product Test"),
            ProductScreen.orderLineHas("Product Test", "1"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            Chrome.clickPlanButton(),
        ].flat(),
});

registry.category("web_tour.tours").add("TableTransferPreparationChange4", {
    steps: () =>
        [
            Chrome.startPoS(),
            //Transfer not sent product on table with same product not sent
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Product Test"),
            ProductScreen.orderlineIsToOrder("Product Test"),
            Chrome.clickPlanButton(),
            FloorScreen.clickTable("4"),
            ProductScreen.clickDisplayedProduct("Product Test"),
            ProductScreen.orderlineIsToOrder("Product Test"),
            ProductScreen.clickControlButton("Transfer"),
            FloorScreen.hasTable("5"),
            FloorScreen.clickTable("5"),
            ProductScreen.orderLineHas("Product Test", "2"),
            ProductScreen.orderlineIsToOrder("Product Test"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            Chrome.clickPlanButton(),
            FloorScreen.clickTable("4"),
            ProductScreen.orderIsEmpty(),
        ].flat(),
});

registry.category("web_tour.tours").add("TableTransferPreparationChange5", {
    steps: () =>
        [
            Chrome.startPoS(),

            //Transfer not sent product on table with same product sent
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Product Test"),
            ProductScreen.orderLineHas("Product Test", "1"),
            ProductScreen.clickOrderButton(),
            Dialog.confirm(),
            ProductScreen.orderlinesHaveNoChange("Product Test"),
            Chrome.clickPlanButton(),
            FloorScreen.clickTable("4"),
            ProductScreen.clickDisplayedProduct("Product Test"),
            ProductScreen.orderLineHas("Product Test", "1"),
            ProductScreen.orderlineIsToOrder("Product Test"),
            ProductScreen.clickControlButton("Transfer"),
            FloorScreen.clickTable("5"),
            ProductScreen.orderlineIsToOrder("Product Test"),
            ProductScreen.orderLineHas("Product Test", "2"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            Chrome.clickPlanButton(),
        ].flat(),
});

registry.category("web_tour.tours").add("TableTransferPreparationChange6", {
    steps: () =>
        [
            Chrome.startPoS(),
            //Transfer not sent product on table without the same product
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Product Test"),
            ProductScreen.clickControlButton("Transfer"),
            FloorScreen.clickTable("4"),
            ProductScreen.orderlineIsToOrder("Product Test"),
            ProductScreen.orderLineHas("Product Test", "1"),
        ].flat(),
});

registry.category("web_tour.tours").add("MultiPreparationPrinter", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Product 1"),
            ProductScreen.clickOrderButton(),
            Dialog.bodyIs("Failed in printing Detailed Receipt changes of the order"),
            Dialog.confirm(),
        ].flat(),
});

registry.category("web_tour.tours").add("LeaveResidualOrder", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.totalAmountIs("2.20"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.clickNextOrder(),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            Chrome.clickPlanButton(),
            FloorScreen.hasTable("2"),
            FloorScreen.hasTable("4"),
            FloorScreen.hasTable("5"),
        ].flat(),
});

registry.category("web_tour.tours").add("FinishResidualOrder", {
    steps: () =>
        [
            Chrome.startPoS(),
            FloorScreen.orderCountSyncedInTableIs("5", "1"),
            FloorScreen.clickTable("5"),
            Order.hasLine({
                productName: "Coca-Cola",
                quantity: 1,
                withClass: ":eq(0)",
            }),
            ProductScreen.totalAmountIs("2.20"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.clickNextOrder(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_combo_preparation_receipt_layout", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Office Combo"),
            combo.select("Combo Product 2"),
            combo.select("Combo Product 4"),
            combo.select("Combo Product 6"),
            Dialog.confirm(),
            {
                trigger: ".actionpad .submit-order.highlight.btn-primary",
            },
            {
                content: "Check if order preparation has product correctly ordered",
                trigger: "body",
                run: async () => {
                    const order = posmodel.get_order();
                    const data = posmodel.getOrderChanges();
                    const changes = Object.values(data.orderlines);
                    const printed = await posmodel.getRenderedReceipt(order, "New", changes);
                    const comboItemLines = [...printed.querySelectorAll(".orderline.mx-5")].map(
                        (el) => el.innerText
                    );
                    const expectedComboItemLines = [
                        "1 Combo Product 2",
                        "1 Combo Product 4",
                        "1 Combo Product 6",
                    ];
                    if (
                        comboItemLines.length !== expectedComboItemLines.length ||
                        !comboItemLines.every((line, index) =>
                            line.includes(expectedComboItemLines[index])
                        )
                    ) {
                        throw new Error("Order line mismatch");
                    }
                },
            },
        ].flat(),
});

registry.category("web_tour.tours").add("test_book_and_release_table", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.bookOrReleaseTable(),
            waitForLoading(),
            {
                content: "Check if order has a server ID",
                trigger: "body",
                run: () => {
                    const order = posmodel.models["pos.order"].getFirst();

                    if (typeof order.id !== "number") {
                        throw new Error("Order does not have a valid server ID");
                    }
                },
            },
            FloorScreen.clickTable("5"),
            ProductScreen.bookOrReleaseTable(),
            waitForLoading(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_combo_synchronisation", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Office Combo"),
            combo.select("Combo Product 2"),
            combo.select("Combo Product 4"),
            combo.select("Combo Product 6"),
            Dialog.confirm(),
            Chrome.clickPlanButton(),
            FloorScreen.clickTable("5"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("A"),
            Chrome.clickPlanButton(),
            FloorScreen.hasTable("5"),
            FloorScreen.clickTable("5"),
            {
                content: "Check if there still has combo lines",
                trigger: ".orderline-combo",
            },
        ].flat(),
});

registry.category("web_tour.tours").add("test_reload_order_line_removed", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            Chrome.clickPlanButton(),
            FloorScreen.clickTable("5"),
            inLeftSide([
                ...ProductScreen.clickLine("Coca-Cola"),
                Numpad.click("⌫"),
                Numpad.click("⌫"),
                ...Order.doesNotHaveLine(),
            ]),
            refresh(),
            FloorScreen.clickTable("5"),
            inLeftSide(Order.hasLine({ productName: "Coca-Cola", quantity: 1 })),
        ].flat(),
});

registry.category("web_tour.tours").add("test_combo_children_qty_updated_with_note", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Office Combo"),
            combo.select("Combo Product 2"),
            combo.select("Combo Product 4"),
            combo.select("Combo Product 6"),
            Dialog.confirm(),
            ProductScreen.clickOrderButton(),
            ProductScreen.clickNumpad("3"),
            ProductScreen.clickInternalNoteButton(),
            TextInputPopup.inputText("test note"),
            Dialog.confirm(),
            combo.select("Combo Product 2"),
            combo.select("Combo Product 4"),
            combo.select("Combo Product 6"),
            Dialog.confirm(),
            Order.doesNotHaveLine({
                productName: "Office Combo",
                quantity: 1,
                internalNote: "test note",
            }),
            Order.hasLine({ productName: "Combo Product 2", quantity: 1 }),
            Order.hasLine({ productName: "Combo Product 4", quantity: 1 }),
            Order.hasLine({ productName: "Combo Product 6", quantity: 1 }),
            Order.hasLine({
                productName: "Office Combo",
                quantity: 2,
                internalNote: "test note",
            }),
            Order.hasLine({ productName: "Combo Product 2", quantity: 2 }),
            Order.hasLine({ productName: "Combo Product 4", quantity: 2 }),
            Order.hasLine({ productName: "Combo Product 6", quantity: 2 }),
        ].flat(),
});
