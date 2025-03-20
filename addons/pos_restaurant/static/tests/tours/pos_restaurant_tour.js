/* global posmodel */

import * as BillScreen from "@pos_restaurant/../tests/tours/utils/bill_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as ReceiptScreen from "@point_of_sale/../tests/pos/tours/utils/receipt_screen_util";
import * as ChromePos from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as ChromeRestaurant from "@pos_restaurant/../tests/tours/utils/chrome";
const Chrome = { ...ChromePos, ...ChromeRestaurant };
import * as FloorScreen from "@pos_restaurant/../tests/tours/utils/floor_screen_util";
import * as ProductScreenPos from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as ProductScreenResto from "@pos_restaurant/../tests/tours/utils/product_screen_util";
import * as TicketScreen from "@point_of_sale/../tests/pos/tours/utils/ticket_screen_util";
import * as combo from "@point_of_sale/../tests/pos/tours/utils/combo_popup_util";
import { inLeftSide } from "@point_of_sale/../tests/pos/tours/utils/common";
import { negateStep } from "@point_of_sale/../tests/generic_helpers/utils";
import { registry } from "@web/core/registry";
import * as Numpad from "@point_of_sale/../tests/generic_helpers/numpad_util";
import { renderToElement } from "@web/core/utils/render";

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
            ProductScreen.clickDisplayedProduct("Awesome Item"),
            ProductScreen.clickDisplayedProduct("Awesome Item"),
            ProductScreen.clickDisplayedProduct("Awesome Item"),
            ProductScreen.totalAmountIs("60.00"),
            ProductScreen.setTab("Test"),
            Chrome.clickPlanButton(),

            // Create first order with 2 products and order them.
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Awesome Thing"),
            ProductScreen.clickDisplayedProduct("Awesome Item"),
            ProductScreen.orderlineIsToOrder("Awesome Thing"),
            ProductScreen.orderlineIsToOrder("Awesome Item"),
            checkOrderChanges([
                { name: "Awesome Thing", quantity: 1 },
                { name: "Awesome Item", quantity: 1 },
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
            ProductScreen.totalAmountIs("50.00"),
            Chrome.clickPlanButton(),

            // Create a second order and pay it.
            FloorScreen.clickTable("2"),
            ProductScreen.clickDisplayedProduct("Awesome Thing", true),
            ProductScreen.clickDisplayedProduct("Awesome Article", true),
            ProductScreen.totalAmountIs("40.00"),
            checkOrderChanges([{ name: "Awesome Thing", quantity: 1 }]),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.clickNextOrder(),

            // order on another table with a product variant and pay it.
            FloorScreen.orderCountSyncedInTableIs("5", "0"),
            FloorScreen.clickTable("4"),
            ProductScreen.clickDisplayedProduct("Awesome Article"),
            Chrome.clickPlanButton(),
            FloorScreen.clickTable("4"),
            ProductScreen.orderlinesHaveNoChange(),
            checkOrderChanges([]),
            ProductScreen.totalAmountIs("10.00"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.clickNextOrder(),

            // After clicking next order, floor screen is shown.
            // It should have 1 as number of draft synced order.
            FloorScreen.orderCountSyncedInTableIs("5", "0"),
            FloorScreen.clickTable("5"),
            ProductScreen.totalAmountIs("50.00"),

            // Create another draft order and go back to floor
            Chrome.clickPlanButton(),
            FloorScreen.clickTable("2"),
            ProductScreen.clickDisplayedProduct("Awesome Article", true),
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
            ProductScreen.totalAmountIs("10.00"),

            // Test transfering an order
            ProductScreen.clickControlButton("Transfer"),
            FloorScreen.clickTable("4"),

            // Test if products still get merged after transfering the order
            ProductScreen.clickDisplayedProduct("Awesome Article"),
            ProductScreen.totalAmountIs("20.00"),
            ProductScreen.clickNumpad("1"),
            ProductScreen.totalAmountIs("10.00"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.clickNextOrder(),
            // At this point, there are no draft orders.

            FloorScreen.clickTable("2"),
            ProductScreen.isShown(),
            ProductScreen.orderIsEmpty(),
            ProductScreen.clickControlButton("Transfer"),
            FloorScreen.clickTable("4"),
            ProductScreen.clickDisplayedProduct("Awesome Item"),
            ProductScreen.totalAmountIs("20.00"),
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
            ProductScreen.clickDisplayedProduct("Awesome Item", true, "1"),
            ProductScreen.clickOrderButton(),
            FloorScreen.clickTable("5"),
            ProductScreen.orderlinesHaveNoChange(),
            Chrome.clickPlanButton(),
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
            ProductScreen.clickDisplayedProduct("Awesome Item"),
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
            ProductScreen.clickDisplayedProduct("Awesome Item"),
            ProductScreen.clickDisplayedProduct("Awesome Item", true, "2"),
            Chrome.clickPlanButton(),
            FloorScreen.clickTable("5"),
            inLeftSide([
                ...ProductScreen.clickLine("Awesome Item", "2"),
                ...ProductScreen.selectedOrderlineHasDirect("Awesome Item", "2"),
                ...["⌫", "1"].map(Numpad.click),
                ...ProductScreen.selectedOrderlineHasDirect("Awesome Item", "1"),
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
            ProductScreen.clickDisplayedProduct("Quality Item"),
            ProductScreen.OrderButtonNotContain("Another one"),
        ].flat(),
});
registry.category("web_tour.tours").add("OrderChange", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Awesome Item", true, "1"),
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
            ProductScreen.clickDisplayedProduct("Awesome Item"),
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
            ProductScreen.clickDisplayedProduct("Awesome Item"),
            ProductScreen.totalAmountIs("20.00"),
            ProductScreen.clickPayButton(),
            PaymentScreen.emptyPaymentlines("20.00"),
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
            ProductScreen.clickDisplayedProduct("Awesome Item"),
            ProductScreen.totalAmountIs("40.00"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentlineDelButton("Bank", "20.00"),
            PaymentScreen.emptyPaymentlines("40.00"),
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
            ProductScreen.clickDisplayedProduct("Awesome Item"),
            ProductScreen.totalAmountIs("60.00"),
            ProductScreen.clickPayButton(),
            PaymentScreen.remainingIs("20.00"),
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
            ProductScreen.clickDisplayedProduct("Configurable 1"),
            Chrome.freezeDateTime(1739370000000),
            Dialog.confirm("Add"),
            ProductScreen.totalAmountIs("11"),
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

                    if (!rendered.innerHTML.includes("One")) {
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
            ProductScreen.clickDisplayedProduct("Awesome Item"),
            ProductScreen.clickOrderButton(),
            Dialog.bodyIs("Failed in printing Preparation Printer, Printer 1 changes of the order"),
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
            ProductScreen.clickDisplayedProduct("Awesome Item"),
            ProductScreen.totalAmountIs("20.00"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.clickNextOrder(),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Awesome Item"),
            Chrome.clickPlanButton(),
        ].flat(),
});

registry.category("web_tour.tours").add("FinishResidualOrder", {
    checkDelay: 50,
    steps: () =>
        [
            Chrome.startPoS(),
            FloorScreen.clickTable("5"),
            ProductScreen.totalAmountIs("20.00"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.clickNextOrder(),
        ].flat(),
});
