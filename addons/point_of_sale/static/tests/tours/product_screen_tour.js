/** @odoo-module */

import * as PaymentScreen from "@point_of_sale/../tests/tours/utils/payment_screen_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as Chrome from "@point_of_sale/../tests/tours/utils/chrome_util";
import * as ReceiptScreen from "@point_of_sale/../tests/tours/utils/receipt_screen_util";
import { registry } from "@web/core/registry";
import * as Order from "@point_of_sale/../tests/tours/utils/generic_components/order_widget_util";
import { inLeftSide } from "@point_of_sale/../tests/tours/utils/common";
import * as ProductConfiguratorPopup from "@point_of_sale/../tests/tours/utils/product_configurator_util";

registry.category("web_tour.tours").add("ProductScreenTour", {
    test: true,
    steps: () =>
        [
            // Go by default to home category

            ProductScreen.clickDisplayedProduct("Desk Organizer", true, "1.0", "5.10"),
            ProductScreen.clickDisplayedProduct("Desk Organizer", true, "2.0", "10.20"),
            ProductScreen.clickDisplayedProduct("Letter Tray", true, "1.0", "5.28"),
            ProductScreen.clickDisplayedProduct("Desk Organizer", true, "3.0", "15.30"),

            // Check effects of clicking numpad buttons
            ProductScreen.clickOrderline("Letter Tray", "1"),
            ProductScreen.checkSelectedOrderlineHas("Letter Tray", "1.0"),
            ProductScreen.clickNumpad("⌫"),
            ProductScreen.checkSelectedOrderlineHas("Letter Tray", "0.0", "0.0"),
            ProductScreen.clickNumpad("⌫"),
            ProductScreen.checkSelectedOrderlineHas("Desk Organizer", "3", "15.30"),
            ProductScreen.clickNumpad("⌫"),
            ProductScreen.checkSelectedOrderlineHas("Desk Organizer", "0.0", "0.0"),
            ProductScreen.clickNumpad("1"),
            ProductScreen.checkSelectedOrderlineHas("Desk Organizer", "1.0", "5.1"),
            ProductScreen.clickNumpad("2"),
            ProductScreen.checkSelectedOrderlineHas("Desk Organizer", "12.0", "61.2"),
            ProductScreen.clickNumpad("3"),
            ProductScreen.checkSelectedOrderlineHas("Desk Organizer", "123.0", "627.3"),
            ProductScreen.clickNumpad(".", "5"),
            ProductScreen.checkSelectedOrderlineHas("Desk Organizer", "123.5", "629.85"),
            ProductScreen.clickNumpad("Price"),
            ProductScreen.checkModeIsActive("Price"),
            ProductScreen.clickNumpad("1"),
            ProductScreen.checkSelectedOrderlineHas("Desk Organizer", "123.5", "123.5"),
            ProductScreen.clickNumpad("1", "."),
            ProductScreen.checkSelectedOrderlineHas("Desk Organizer", "123.5", "1,358.5"),
            ProductScreen.clickNumpad("% Disc"),
            ProductScreen.checkModeIsActive("% Disc"),
            ProductScreen.clickNumpad("5", "."),
            ProductScreen.checkSelectedOrderlineHas("Desk Organizer", "123.5", "1,290.58"),
            ProductScreen.clickNumpad("Qty"),
            ProductScreen.clickNumpad("⌫"),
            ProductScreen.clickNumpad("⌫"),
            ProductScreen.checkOrderIsEmpty(),

            // Check different subcategories
            ProductScreen.clickSubcategory("Desk test"),
            ProductScreen.checkProductIsDisplayed("Desk Pad"),
            ProductScreen.goBackToMainScreen(),
            ProductScreen.checkProductIsDisplayed("Desk Pad"),
            ProductScreen.clickSubcategory("Misc test"),
            ProductScreen.checkProductIsDisplayed("Whiteboard Pen"),
            ProductScreen.checkProductIsDisplayed("Whiteboard Pen"),
            ProductScreen.goBackToMainScreen(),
            ProductScreen.clickSubcategory("Chair test"),
            ProductScreen.checkProductIsDisplayed("Letter Tray"),
            ProductScreen.checkProductIsDisplayed("Letter Tray"),
            ProductScreen.goBackToMainScreen(),
            ProductScreen.clickSubcategory("Chair test"),

            // Add two orderlines and update quantity
            ProductScreen.clickDisplayedProduct("Whiteboard Pen"),
            ProductScreen.clickDisplayedProduct("Wall Shelf Unit"),
            ProductScreen.clickOrderline("Whiteboard Pen", "1.0"),
            ProductScreen.clickNumpad("2"),
            ProductScreen.checkSelectedOrderlineHas("Whiteboard Pen", "2.0"),
            ProductScreen.clickOrderline("Wall Shelf Unit", "1.0"),
            ProductScreen.clickNumpad("2"),
            ProductScreen.checkSelectedOrderlineHas("Wall Shelf Unit", "2.0"),
            ProductScreen.clickNumpad("⌫"),
            ProductScreen.checkSelectedOrderlineHas("Wall Shelf Unit", "0.0"),
            ProductScreen.clickNumpad("⌫"),
            ProductScreen.checkSelectedOrderlineHas("Whiteboard Pen", "2.0"),
            ProductScreen.clickNumpad("⌫"),
            ProductScreen.checkSelectedOrderlineHas("Whiteboard Pen", "0.0"),
            ProductScreen.clickNumpad("⌫"),
            ProductScreen.checkOrderIsEmpty(),

            // Add multiple orderlines then delete each of them until empty
            ProductScreen.clickDisplayedProduct("Whiteboard Pen"),
            ProductScreen.clickDisplayedProduct("Wall Shelf Unit"),
            ProductScreen.clickDisplayedProduct("Small Shelf"),
            ProductScreen.clickDisplayedProduct("Magnetic Board"),
            ProductScreen.clickDisplayedProduct("Monitor Stand"),
            ProductScreen.clickOrderline("Whiteboard Pen", "1.0"),
            ProductScreen.clickNumpad("⌫"),
            ProductScreen.checkSelectedOrderlineHas("Whiteboard Pen", "0.0"),
            ProductScreen.clickNumpad("⌫"),
            ProductScreen.checkSelectedOrderlineHas("Monitor Stand", "1.0"),
            ProductScreen.clickOrderline("Wall Shelf Unit", "1.0"),
            ProductScreen.clickNumpad("⌫"),
            ProductScreen.checkSelectedOrderlineHas("Wall Shelf Unit", "0.0"),
            ProductScreen.clickNumpad("⌫"),
            ProductScreen.checkSelectedOrderlineHas("Monitor Stand", "1.0"),
            ProductScreen.clickOrderline("Small Shelf", "1.0"),
            ProductScreen.clickNumpad("⌫"),
            ProductScreen.checkSelectedOrderlineHas("Small Shelf", "0.0"),
            ProductScreen.clickNumpad("⌫"),
            ProductScreen.checkSelectedOrderlineHas("Monitor Stand", "1.0"),
            ProductScreen.clickOrderline("Magnetic Board", "1.0"),
            ProductScreen.clickNumpad("⌫"),
            ProductScreen.checkSelectedOrderlineHas("Magnetic Board", "0.0"),
            ProductScreen.clickNumpad("⌫"),
            ProductScreen.checkSelectedOrderlineHas("Monitor Stand", "1.0"),
            ProductScreen.clickNumpad("⌫"),
            ProductScreen.checkSelectedOrderlineHas("Monitor Stand", "0.0"),
            ProductScreen.clickNumpad("⌫"),
            ProductScreen.checkOrderIsEmpty(),

            // Test OrderlineCustomerNoteButton
            ProductScreen.clickDisplayedProduct("Desk Organizer", true, "1.0"),
            ProductScreen.addCustomerNote("Test customer note"),
            inLeftSide(
                Order.hasLine({
                    productName: "Desk Organizer",
                    quantity: "1.0",
                    customerNote: "Test customer note",
                    withClass: ".selected",
                })
            ),
            ProductScreen.isShown(),
        ].flat(),
});

registry.category("web_tour.tours").add("FiscalPositionNoTax", {
    test: true,
    steps: () =>
        [
            Dialog.confirm("Open session"),
            ProductScreen.clickDisplayedProduct("Test Product"),
            ProductScreen.checkTotalAmountIs("100.00"),
            ProductScreen.clickFiscalPosition("No Tax"),
            ProductScreen.checkNoDiscountApplied("100.00"),
            ProductScreen.checkTotalAmountIs("86.96"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank", true, { remaining: "0.00" }),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            Order.checkDoesNotHaveLine({ discount: "" }),
        ].flat(),
});

registry.category("web_tour.tours").add("CashClosingDetails", {
    test: true,
    steps: () =>
        [
            ProductScreen.enterOpeningAmount("90"),
            Dialog.confirm("Open session"),
            ProductScreen.checkSecondCashClosingDetailsLineAmount("10.00", "-"),
        ].flat(),
});

registry.category("web_tour.tours").add("ShowTaxExcludedTour", {
    test: true,
    steps: () =>
        [
            Dialog.confirm("Open session"),

            ProductScreen.clickDisplayedProduct("Test Product", true, "1.0", "100.0"),
            ProductScreen.checkTotalAmountIs("110.0"),
            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("limitedProductPricelistLoading", {
    test: true,
    steps: () =>
        [
            Dialog.confirm("Open session"),

            ProductScreen.scan_barcode("0100100"),
            ProductScreen.checkSelectedOrderlineHas("Test Product 1", "1.0", "80.0"),

            ProductScreen.scan_barcode("0100201"),
            ProductScreen.checkSelectedOrderlineHas("Test Product 2 (White)", "1.0", "100.0"),

            ProductScreen.scan_barcode("0100202"),
            ProductScreen.checkSelectedOrderlineHas("Test Product 2 (Red)", "1.0", "120.0"),

            ProductScreen.scan_barcode("0100300"),
            ProductScreen.checkSelectedOrderlineHas("Test Product 3", "1.0", "50.0"),
            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("MultiProductOptionsTour", {
    test: true,
    steps: () =>
        [
            Dialog.confirm("Open session"),

            ProductScreen.clickDisplayedProduct("Product A"),
            ProductConfiguratorPopup.checkOptionIsShown("Value 1"),
            ProductConfiguratorPopup.checkOptionIsShown("Value 2"),
            Dialog.confirm("Ok"),

            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("TranslateProductNameTour", {
    test: true,
    steps: () =>
        [
            Dialog.confirm("Ouvrir la session"),
            ProductScreen.clickDisplayedProduct("Testez le produit"),
            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("DecimalCommaOrderlinePrice", {
    test: true,
    steps: () =>
        [
            Dialog.confirm("Open session"),
            ProductScreen.clickDisplayedProduct("Test Product"),
            ProductScreen.clickNumpad("5"),
            ProductScreen.checkSelectedOrderlineHas("Test Product", "5,00", "7.267,65"),
            Chrome.endTour(),
        ].flat(),
});
