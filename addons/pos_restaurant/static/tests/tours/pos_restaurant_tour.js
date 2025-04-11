/* global posmodel */

import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as ReceiptScreen from "@point_of_sale/../tests/pos/tours/utils/receipt_screen_util";
import * as ChromePos from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as ChromeRestaurant from "@pos_restaurant/../tests/tours/utils/chrome";
const Chrome = { ...ChromePos, ...ChromeRestaurant };
import * as FloorScreen from "@pos_restaurant/../tests/tours/utils/floor_screen_util";
import * as ProductScreenPos from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as ProductScreenResto from "@pos_restaurant/../tests/tours/utils/product_screen_util";
import * as Order from "@point_of_sale/../tests/generic_helpers/order_widget_util";
import * as TicketScreen from "@point_of_sale/../tests/pos/tours/utils/ticket_screen_util";
import * as combo from "@point_of_sale/../tests/pos/tours/utils/combo_popup_util";
import { inLeftSide } from "@point_of_sale/../tests/pos/tours/utils/common";
import { registry } from "@web/core/registry";
import * as Numpad from "@point_of_sale/../tests/generic_helpers/numpad_util";
import { renderToElement } from "@web/core/utils/render";
import { delay } from "@odoo/hoot-dom";

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
            FloorScreen.clickNewOrder(),

            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.setTab("Test"),
            Chrome.clickPlanButton(),

            // Create first order
            FloorScreen.clickTable("5"),
            Chrome.isTabActive("5"),
            ProductScreen.clickDisplayedProduct("Coca-Cola", true),
            inLeftSide(Order.hasLine({ productName: "Coca-Cola", run: "dblclick" })),
            ProductScreen.clickDisplayedProduct("Water", true),
            ProductScreen.orderlineIsToOrder("Water"),
            ProductScreen.orderlineIsToOrder("Coca-Cola"),
            checkOrderChanges([
                { name: "Water", quantity: 1 },
                { name: "Coca-Cola", quantity: 1 },
            ]),
            ProductScreen.clickOrderButton(),
            {
                ...Dialog.confirm(),
                content:
                    "acknowledge printing error ( because we don't have printer in the test. )",
            },
            FloorScreen.clickTable("5"),
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

            // order on another table with a product variant
            FloorScreen.orderCountSyncedInTableIs("5", "0"),
            FloorScreen.clickTable("4"),
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
            FloorScreen.clickTable("4"),
            ProductScreen.orderlinesHaveNoChange(),
            checkOrderChanges([]),
            ProductScreen.totalAmountIs("5.87"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.clickNextOrder(),

            // After clicking next order, floor screen is shown.
            // It should have 1 as number of draft synced order.
            FloorScreen.orderCountSyncedInTableIs("5", "0"),
            FloorScreen.clickTable("5"),
            ProductScreen.totalAmountIs("4.40"),

            // Create another draft order and go back to floor
            Chrome.clickPlanButton(),
            FloorScreen.clickTable("2"),
            ProductScreen.clickDisplayedProduct("Coca-Cola", true),
            ProductScreen.clickDisplayedProduct("Minute Maid", true),
            Chrome.clickPlanButton(),
            FloorScreen.orderCountSyncedInTableIs("5", "0"),

            // Delete the first order then go back to floor
            Chrome.clickOrders(),
            // The order ref ends with -00002 because it is actually the 2nd order made in the session.
            // The first order made in the session is a floating order.
            TicketScreen.deleteOrder("002"),
            Dialog.confirm(),
            {
                ...Dialog.confirm(),
                content:
                    "acknowledge printing error ( because we don't have printer in the test. )",
            },
            Chrome.isSyncStatusConnected(),
            TicketScreen.selectOrder("005"),
            TicketScreen.loadSelectedOrder(),
            ProductScreen.isShown(),
            Chrome.clickPlanButton(),

            // There should be 0 synced draft order as we already deleted -00002.
            FloorScreen.clickTable("5"),
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
            FloorScreen.clickTable("2"),
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

            // Test if products still get merged after transfering the order
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
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
            ProductScreen.clickDisplayedProduct("Coca-Cola", true, "1"),
            ProductScreen.clickOrderButton(),
            FloorScreen.clickTable("5"),
            ProductScreen.orderlinesHaveNoChange(),
            Chrome.clickPlanButton(),
        ].flat(),
});

registry.category("web_tour.tours").add("OrderTrackingTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.clickDisplayedProduct("Coca-Cola", true, "2"),
            Chrome.clickPlanButton(),
            FloorScreen.clickTable("5"),
            inLeftSide([
                ...ProductScreen.clickLine("Coca-Cola", "2"),
                ...ProductScreen.selectedOrderlineHasDirect("Coca-Cola", "2"),
                ...["⌫", "1"].map(Numpad.click),
                ...ProductScreen.selectedOrderlineHasDirect("Coca-Cola", "1"),
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
            ProductScreen.clickDisplayedProduct("Coca-Cola", true, "1"),
            ProductScreen.clickOrderButton(),
            {
                ...Dialog.confirm(),
                content:
                    "acknowledge printing error ( because we don't have printer in the test. )",
            },
            FloorScreen.clickTable("5"),
            ProductScreen.orderlinesHaveNoChange(),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickNumpad("+10"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            TicketScreen.receiptChangeIs("10"),
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
                    const order = posmodel.getOrder();
                    const orderChange = posmodel.changesToOrder(
                        order,
                        posmodel.config.preparationCategories,
                        false
                    );
                    const { orderData, changes } = posmodel.generateOrderChange(
                        order,
                        orderChange,
                        Array.from(posmodel.config.preparationCategories),
                        false
                    );

                    orderData.changes = {
                        title: "new",
                        data: changes.new,
                    };

                    const rendered = renderToElement("point_of_sale.OrderChangeReceipt", {
                        data: orderData,
                    });

                    if (!rendered.innerHTML.includes("Value 1")) {
                        throw new Error("Value 1 not found in printed receipt");
                    }
                    if (!rendered.innerHTML.includes("14:20")) {
                        throw new Error("14:20 not found in printed receipt");
                    }
                },
            },
        ].flat(),
});

registry.category("web_tour.tours").add("test_combo_preparation_receipt", {
    checkDelay: 50,
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
                    const order = posmodel.getOrder();
                    const orderChange = posmodel.changesToOrder(
                        order,
                        posmodel.config.preparationCategories,
                        false
                    );
                    const { orderData, changes } = posmodel.generateOrderChange(
                        order,
                        orderChange,
                        Array.from(posmodel.config.preparationCategories),
                        false
                    );

                    orderData.changes = {
                        title: "new",
                        data: changes.new,
                    };

                    const rendered = renderToElement("point_of_sale.OrderChangeReceipt", {
                        data: orderData,
                    });
                    const orderLines = [...rendered.querySelectorAll(".orderline")];
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

registry.category("web_tour.tours").add("MultiPreparationPrinter", {
    checkDelay: 50,
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Product 1"),
            ProductScreen.clickOrderButton(),
            Dialog.bodyIs("Failed in printing Printer 2 changes of the order"),
            Dialog.confirm(),
        ].flat(),
});

registry.category("web_tour.tours").add("LeaveResidualOrder", {
    checkDelay: 50,
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
        ].flat(),
});

registry.category("web_tour.tours").add("FinishResidualOrder", {
    checkDelay: 50,
    steps: () =>
        [
            Chrome.startPoS(),
            FloorScreen.clickTable("5"),
            ProductScreen.totalAmountIs("2.20"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.clickNextOrder(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_multiple_preparation_printer_different_categories", {
    checkDelay: 50,
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Product 1"),
            ProductScreen.clickDisplayedProduct("Product 2"),
            ProductScreen.clickOrderButton(),
            Dialog.bodyIs("Failed in printing Printer 1, Printer 2 changes of the order"),
            Dialog.confirm(),
        ].flat(),
});
