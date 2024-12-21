import * as BillScreen from "@pos_restaurant/../tests/tours/utils/bill_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/tours/utils/payment_screen_util";
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
import { inLeftSide, negateStep } from "@point_of_sale/../tests/tours/utils/common";
import { registry } from "@web/core/registry";
import * as Numpad from "@point_of_sale/../tests/tours/utils/numpad_util";

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
            {
                ...Dialog.confirm(),
                content:
                    "acknowledge printing error ( because we don't have printer in the test. )",
            },
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
            TicketScreen.deleteOrder("-0002"),
            Dialog.confirm(),
            {
                ...Dialog.confirm(),
                content:
                    "acknowledge printing error ( because we don't have printer in the test. )",
            },
            Chrome.isSyncStatusConnected(),
            TicketScreen.selectOrder("-0005"),
            TicketScreen.loadSelectedOrder(),
            ProductScreen.isShown(),
            Chrome.clickPlanButton(),

            // There should be 0 synced draft order as we already deleted -0002.
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
            ProductScreen.clickControlButton("Transfer"),
            FloorScreen.clickTable("4"),
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
            ProductScreen.clickOrderButton(),
            ProductScreen.orderlinesHaveNoChange(),
            Chrome.clickPlanButton(),
        ].flat(),
});

const billScreenQRCode = {
    content: "QR codes are shown",
    trigger: ".pos-receipt #posqrcode",
};

registry.category("web_tour.tours").add("BillScreenTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.clickControlButton("Bill"),
            // HACK: is_modal should be false so that the trigger can be found.
            { ...negateStep(billScreenQRCode) },
            BillScreen.closeBillPopup(),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            billScreenQRCode,
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
            {
                content:
                    "As the font can't be loaded, we wait printing failed modal before close tour",
                trigger: ".modal:contains(printing failed)",
            },
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
        ].flat(),
});
