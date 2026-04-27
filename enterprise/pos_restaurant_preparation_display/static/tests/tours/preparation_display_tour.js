/* global posmodel */
import * as Order from "@point_of_sale/../tests/tours/utils/generic_components/order_widget_util";
import * as PaymentScreen from "@point_of_sale/../tests/tours/utils/payment_screen_util";
import * as ReceiptScreen from "@point_of_sale/../tests/tours/utils/receipt_screen_util";
import * as Chrome from "@point_of_sale/../tests/tours/utils/chrome_util";
import * as FloorScreen from "@pos_restaurant/../tests/tours/utils/floor_screen_util";
import * as ProductScreenPos from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import * as ProductScreenResto from "@pos_restaurant/../tests/tours/utils/product_screen_util";
import * as PreparationDisplay from "@pos_restaurant_preparation_display/../tests/tours/utils/preparation_display_util";
import * as Numpad from "@point_of_sale/../tests/tours/utils/numpad_util";
import { inLeftSide } from "@point_of_sale/../tests/tours/utils/common";
const ProductScreen = { ...ProductScreenPos, ...ProductScreenResto, ...PreparationDisplay };
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("PreparationDisplayTourResto", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            // Create first order
            FloorScreen.clickTable("5"),
            ProductScreen.orderBtnIsPresent(),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.clickDisplayedProduct("Water"),
            ProductScreen.orderlineIsToOrder("Water"),
            ProductScreen.orderlineIsToOrder("Coca-Cola"),
            ProductScreen.clickOrderButton(),
            ProductScreen.orderlinesHaveNoChange(),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            ReceiptScreen.clickNextOrder(),

            // Create second order
            FloorScreen.isShown(),
            FloorScreen.clickTable("4"),
            ProductScreen.orderBtnIsPresent(),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.orderlineIsToOrder("Coca-Cola"),
            ProductScreen.clickOrderButton(),
            ProductScreen.orderlinesHaveNoChange(),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            ReceiptScreen.clickNextOrder(),

            // Create third order
            FloorScreen.isShown(),
            FloorScreen.clickTable("4"),
            ProductScreen.orderBtnIsPresent(),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.clickDisplayedProduct("Water"),
            ProductScreen.clickDisplayedProduct("Minute Maid"),
            ProductScreen.orderlineIsToOrder("Coca-Cola"),
            ProductScreen.orderlineIsToOrder("Water"),
            ProductScreen.orderlineIsToOrder("Minute Maid"),
            ProductScreen.clickOrderButton(),
            ProductScreen.orderlinesHaveNoChange(),
            ProductScreen.selectedOrderlineHas("Minute Maid", "1.00"),
            ProductScreen.clickNumpad("⌫"),
            ProductScreen.selectedOrderlineHas("Minute Maid", "0.00"),
            ProductScreen.orderlineIsToOrder("Minute Maid"),
            ProductScreen.clickOrderButton(),
            ProductScreen.orderlinesHaveNoChange(),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            ReceiptScreen.clickNextOrder(),
        ].flat(),
});

registry.category("web_tour.tours").add("PreparationDisplayTourInternalNotes", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.addInternalNote("Test Internal Notes"),
            ProductScreen.orderlineIsToOrder("Coca-Cola"),
            ProductScreen.clickOrderButton(),
            ProductScreen.orderlinesHaveNoChange(),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.clickOrderButton(),
            ProductScreen.orderlinesHaveNoChange(),
            Order.hasLine({
                productName: "Coca-Cola",
                internalNote: "Test Internal Notes",
            }),
            Order.hasLine({
                productName: "Coca-Cola",
                internalNote: "",
            }),
            Chrome.clickPlanButton(),
        ].flat(),
});

registry.category("web_tour.tours").add("PreparationDisplayTourResto2", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            // Create first order
            FloorScreen.clickTable("5"),
            ProductScreen.orderBtnIsPresent(),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.orderlineIsToOrder("Coca-Cola"),
            ProductScreen.clickOrderButton(),
            Chrome.waitRequest(),
            ProductScreen.orderlinesHaveNoChange(),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.orderlineIsToOrder("Coca-Cola"),
            ProductScreen.clickOrderButton(),
            Chrome.waitRequest(),
            ProductScreen.orderlinesHaveNoChange(),
            Chrome.clickPlanButton(),
        ].flat(),
});

registry.category("web_tour.tours").add("PreparationDisplayCancelOrderTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.orderBtnIsPresent(),
            ProductScreen.clickDisplayedProduct("Test Food"),
            ProductScreen.orderlineIsToOrder("Test Food"),
            ProductScreen.clickOrderButton(),
            ProductScreen.orderlinesHaveNoChange(),
            ProductScreen.clickReview(),
            ProductScreen.clickControlButton("Cancel Order"),
            Dialog.confirm(),
            FloorScreen.isShown(),
        ].flat(),
});

registry.category("web_tour.tours").add("PreparationDisplayTourSkipChange", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            // Create first order
            FloorScreen.clickTable("5"),
            ProductScreen.orderBtnIsPresent(),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.doubleClickLine("Coca-Cola"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.clickDisplayedProduct("Water"),
            ProductScreen.clickOrderButton(),
            ProductScreen.orderlinesHaveNoChange(),
            ProductScreen.clickDisplayedProduct("Minute Maid"),
            ProductScreen.clickOrderButton(),
            ProductScreen.orderlinesHaveNoChange(),
        ].flat(),
});

registry.category("web_tour.tours").add("PreparationDisplayPaymentNotCancelDisplayTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            // Test to ensure no traceback occurs when releasing a table after deleting a synced order
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Coca-cola"),
            clickOrderButton(),
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
            inLeftSide([Numpad.click("⌫"), Numpad.click("⌫")]),
            ProductScreen.bookOrReleaseTable(),
            Chrome.isSynced(),
            FloorScreen.isShown(),

            FloorScreen.clickTable("5"),
            ProductScreen.addOrderline("Coca-Cola", "2"),
            ProductScreen.addInternalNote("To Serve"),
            ProductScreen.clickOrderButton(),
            ProductScreen.orderlinesHaveNoChange(),
            ProductScreen.addOrderline("Coca-Cola", "2"),
            ProductScreen.addInternalNote("To Serve"),
            ProductScreen.clickOrderButton(),
            ProductScreen.orderlinesHaveNoChange(),
            ProductScreen.clickNumpad("⌫"),
            ProductScreen.clickNumpad("1"),
            Order.hasLine({
                productName: "Coca-Cola",
                quantity: 1,
                withClass: ":eq(1)",
            }),
            {
                trigger: ".submit-order:contains(-1)",
            },
            ProductScreen.clickOrderButton(),
            Order.hasLine({
                productName: "Coca-Cola",
                quantity: 2,
                withClass: ":eq(0)",
            }),
            Order.hasLine({
                productName: "Coca-Cola",
                quantity: 1,
                withClass: ":eq(1)",
            }),
            ProductScreen.orderlinesHaveNoChange(),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            ProductScreen.orderlinesHaveNoChange(),
            Chrome.endTour(),
        ].flat(),
});

function clickOrderButton() {
    return [
        ProductScreen.clickOrderButton(),
        Chrome.waitRequest(),
        ProductScreen.orderlinesHaveNoChange(),
    ].flat();
}

registry.category("web_tour.tours").add("test_update_internal_note_of_order", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickSubcategory("Test-cat"),
            ProductScreen.orderBtnIsPresent(),
            ProductScreen.clickDisplayedProduct("Demo Food"),
            ProductScreen.clickDisplayedProduct("Test Food"),
            ProductScreen.orderlineIsToOrder("Test Food"),
            clickOrderButton(),
            ProductScreen.addInternalNote("Test Internal Notes"),
            ProductScreen.selectedOrderlineHas("Test Food", "1.0"),
            ProductScreen.clickNumpad("⌫"),
            ProductScreen.selectedOrderlineHas("Test Food", "0.0"),
            ProductScreen.clickNumpad("⌫"),
            ProductScreen.selectedOrderlineHas("Demo Food", "1.0"),
            clickOrderButton(),
            ProductScreen.totalAmountIs("10"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
        ].flat(),
});
