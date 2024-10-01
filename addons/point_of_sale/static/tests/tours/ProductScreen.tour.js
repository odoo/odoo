/** @odoo-module */

import * as PaymentScreen from "@point_of_sale/../tests/tours/helpers/PaymentScreenTourMethods";
import * as Dialog from "@point_of_sale/../tests/tours/helpers/DialogTourMethods";
import * as PartnerList from "@point_of_sale/../tests/tours/helpers/PartnerListTourMethods";
import * as ProductScreen from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import * as ProductScreenPartnerList from "@point_of_sale/../tests/tours/helpers/ProductScreenPartnerListTourMethods";
import * as Chrome from "@point_of_sale/../tests/tours/helpers/ChromeTourMethods";
import * as ReceiptScreen from "@point_of_sale/../tests/tours/helpers/ReceiptScreenTourMethods";
import { registry } from "@web/core/registry";
import * as Order from "@point_of_sale/../tests/tours/helpers/generic_components/OrderWidgetMethods";
import * as ProductConfiguratorPopup from "@point_of_sale/../tests/tours/helpers/ProductConfiguratorTourMethods";
import {
    inLeftSide,
    scan_barcode,
    selectButton,
    refresh,
} from "@point_of_sale/../tests/tours/helpers/utils";

registry.category("web_tour.tours").add("ProductScreenTour", {
    test: true,
    url: "/pos/ui",
    steps: () =>
        [
            // Go by default to home category
            ProductScreen.clickShowProductsMobile(),
            // Clicking product multiple times should increment quantity
            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            ProductScreen.selectedOrderlineHas("Desk Organizer", "1.0", "5.10"),
            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            ProductScreen.selectedOrderlineHas("Desk Organizer", "2.0", "10.20"),

            // Clicking product should add new orderline and select the orderline
            // If orderline exists, increment the quantity
            ProductScreen.clickDisplayedProduct("Letter Tray"),
            ProductScreen.selectedOrderlineHas("Letter Tray", "1.0", "5.28"),
            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            ProductScreen.selectedOrderlineHas("Desk Organizer", "3.0", "15.30"),

            // Check effects of clicking numpad buttons
            ProductScreen.clickOrderline("Letter Tray", "1"),
            ProductScreen.selectedOrderlineHas("Letter Tray", "1.0"),
            ProductScreen.pressNumpad("⌫"),
            ProductScreen.selectedOrderlineHas("Letter Tray", "0.0", "0.0"),
            ProductScreen.pressNumpad("⌫"),
            ProductScreen.selectedOrderlineHas("Desk Organizer", "3", "15.30"),
            ProductScreen.pressNumpad("⌫"),
            ProductScreen.selectedOrderlineHas("Desk Organizer", "0.0", "0.0"),
            ProductScreen.pressNumpad("1"),
            ProductScreen.selectedOrderlineHas("Desk Organizer", "1.0", "5.1"),
            ProductScreen.pressNumpad("2"),
            ProductScreen.selectedOrderlineHas("Desk Organizer", "12.0", "61.2"),
            ProductScreen.pressNumpad("3"),
            ProductScreen.selectedOrderlineHas("Desk Organizer", "123.0", "627.3"),
            ProductScreen.pressNumpad(".", "5"),
            ProductScreen.selectedOrderlineHas("Desk Organizer", "123.5", "629.85"),
            ProductScreen.pressNumpad("Price"),
            ProductScreen.modeIsActive("Price"),
            ProductScreen.pressNumpad("1"),
            ProductScreen.selectedOrderlineHas("Desk Organizer", "123.5", "123.5"),
            ProductScreen.pressNumpad("1", "."),
            ProductScreen.selectedOrderlineHas("Desk Organizer", "123.5", "1,358.5"),
            ProductScreen.pressNumpad("% Disc"),
            ProductScreen.modeIsActive("% Disc"),
            ProductScreen.pressNumpad("5", "."),
            ProductScreen.selectedOrderlineHas("Desk Organizer", "123.5", "1,290.58"),
            ProductScreen.pressNumpad("Qty"),
            ProductScreen.pressNumpad("⌫"),
            ProductScreen.pressNumpad("⌫"),
            ProductScreen.orderIsEmpty(),

            // Check different subcategories
            ProductScreen.goBackToMainScreen(),
            ProductScreen.clickSubcategory("Desk test"),
            ProductScreen.productIsDisplayed("Desk Pad"),
            ProductScreen.goBackToMainScreen(),
            ProductScreen.clickSubcategory("Misc test"),
            ProductScreen.productIsDisplayed("Whiteboard Pen"),
            ProductScreen.goBackToMainScreen(),
            ProductScreen.clickSubcategory("Chair test"),
            ProductScreen.productIsDisplayed("Letter Tray"),
            ProductScreen.goBackToMainScreen(),
            ProductScreen.clickSubcategory("Chair test"),
            ProductScreen.goBackToMainScreen(),

            // Add two orderlines and update quantity
            ProductScreen.clickShowProductsMobile(),
            ProductScreen.clickDisplayedProduct("Whiteboard Pen"),
            ProductScreen.clickDisplayedProduct("Wall Shelf Unit"),
            ProductScreen.clickOrderline("Whiteboard Pen", "1.0"),
            ProductScreen.pressNumpad("2"),
            ProductScreen.selectedOrderlineHas("Whiteboard Pen", "2.0"),
            ProductScreen.clickOrderline("Wall Shelf Unit", "1.0"),
            ProductScreen.pressNumpad("2"),
            ProductScreen.selectedOrderlineHas("Wall Shelf Unit", "2.0"),
            ProductScreen.pressNumpad("⌫"),
            ProductScreen.selectedOrderlineHas("Wall Shelf Unit", "0.0"),
            ProductScreen.pressNumpad("⌫"),
            ProductScreen.selectedOrderlineHas("Whiteboard Pen", "2.0"),
            ProductScreen.pressNumpad("⌫"),
            ProductScreen.selectedOrderlineHas("Whiteboard Pen", "0.0"),
            ProductScreen.pressNumpad("⌫"),
            ProductScreen.orderIsEmpty(),

            // Add multiple orderlines then delete each of them until empty
            ProductScreen.clickDisplayedProduct("Whiteboard Pen"),
            ProductScreen.clickDisplayedProduct("Wall Shelf Unit"),
            ProductScreen.clickDisplayedProduct("Small Shelf"),
            ProductScreen.clickDisplayedProduct("Magnetic Board"),
            ProductScreen.clickDisplayedProduct("Monitor Stand"),
            ProductScreen.clickOrderline("Whiteboard Pen", "1.0"),
            ProductScreen.pressNumpad("⌫"),
            ProductScreen.selectedOrderlineHas("Whiteboard Pen", "0.0"),
            ProductScreen.pressNumpad("⌫"),
            ProductScreen.selectedOrderlineHas("Monitor Stand", "1.0"),
            ProductScreen.clickOrderline("Wall Shelf Unit", "1.0"),
            ProductScreen.pressNumpad("⌫"),
            ProductScreen.selectedOrderlineHas("Wall Shelf Unit", "0.0"),
            ProductScreen.pressNumpad("⌫"),
            ProductScreen.selectedOrderlineHas("Monitor Stand", "1.0"),
            ProductScreen.clickOrderline("Small Shelf", "1.0"),
            ProductScreen.pressNumpad("⌫"),
            ProductScreen.selectedOrderlineHas("Small Shelf", "0.0"),
            ProductScreen.pressNumpad("⌫"),
            ProductScreen.selectedOrderlineHas("Monitor Stand", "1.0"),
            ProductScreen.clickOrderline("Magnetic Board", "1.0"),
            ProductScreen.pressNumpad("⌫"),
            ProductScreen.selectedOrderlineHas("Magnetic Board", "0.0"),
            ProductScreen.pressNumpad("⌫"),
            ProductScreen.selectedOrderlineHas("Monitor Stand", "1.0"),
            ProductScreen.pressNumpad("⌫"),
            ProductScreen.selectedOrderlineHas("Monitor Stand", "0.0"),
            ProductScreen.pressNumpad("⌫"),
            ProductScreen.orderIsEmpty(),

            // Test OrderlineCustomerNoteButton
            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            ProductScreen.selectedOrderlineHas("Desk Organizer", "1.0"),
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
    url: "/pos/ui",
    steps: () =>
        [
            Dialog.confirm("Open session"),
            ProductScreen.clickShowProductsMobile(),
            ProductScreen.clickDisplayedProduct("Test Product"),
            ProductScreen.totalAmountIs("100.00"),
            ProductScreen.changeFiscalPosition("No Tax"),
            ProductScreen.noDiscountApplied("100.00"),
            ProductScreen.totalAmountIs("86.96"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.remainingIs("0.00"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            Order.doesNotHaveLine({ discount: "" }),
        ].flat(),
});

registry.category("web_tour.tours").add("CashClosingDetails", {
    test: true,
    url: "/pos/ui",
    steps: () =>
        [
            ProductScreen.enterOpeningAmount("90"),
            Dialog.confirm("Open session"),
            ProductScreen.checkSecondCashClosingDetailsLineAmount("10.00", "-"),
        ].flat(),
});

registry.category("web_tour.tours").add("ShowTaxExcludedTour", {
    test: true,
    url: "/pos/ui",
    steps: () =>
        [
            Dialog.confirm("Open session"),

            ProductScreen.clickShowProductsMobile(),
            ProductScreen.clickDisplayedProduct("Test Product"),
            ProductScreen.selectedOrderlineHas("Test Product", "1.0", "100.0"),
            ProductScreen.totalAmountIs("110.0"),
            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("limitedProductPricelistLoading", {
    test: true,
    url: "/pos/ui",
    steps: () =>
        [
            Dialog.confirm("Open session"),

            scan_barcode("0100100"),
            ProductScreen.selectedOrderlineHas("Test Product 1", "1.0", "80.0"),

            scan_barcode("0100201"),
            ProductScreen.selectedOrderlineHas("Test Product 2 (White)", "1.0", "100.0"),

            scan_barcode("0100202"),
            ProductScreen.selectedOrderlineHas("Test Product 2 (Red)", "1.0", "120.0"),

            scan_barcode("0100300"),
            ProductScreen.selectedOrderlineHas("Test Product 3", "1.0", "50.0"),
            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("MultiProductOptionsTour", {
    test: true,
    steps: () =>
        [
            Dialog.confirm("Open session"),

            ProductScreen.clickShowProductsMobile(),
            ProductScreen.clickDisplayedProduct("Product A"),
            ProductConfiguratorPopup.isOptionShown("Value 1"),
            ProductConfiguratorPopup.isOptionShown("Value 2"),
            Dialog.confirm("Ok"),

            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("TranslateProductNameTour", {
    test: true,
    url: "/pos/ui",
    steps: () =>
        [
            Dialog.confirm("Ouvrir la session"),

            ProductScreen.clickShowProductsMobile(),

            ProductScreen.clickDisplayedProduct("Testez le produit"),

            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("CheckProductInformation", {
    test: true,
    url: "/pos/ui",
    steps: () =>
        [
            Dialog.confirm("Open session"),
            ProductScreen.clickShowProductsMobile(),
            ProductScreen.clickInfoProduct("product_a"),
            {
                trigger: ".section-financials :contains('Margin')",
                run: () => {},
            },
        ].flat(),
});

registry.category("web_tour.tours").add("PosCustomerAllFieldsDisplayed", {
    test: true,
    url: "/pos/ui",
    steps: () =>
        [
            Dialog.confirm("Open session"),
            ProductScreen.clickPartnerButton(),
            PartnerList.checkContactValues(
                "John Doe",
                "1 street of astreet",
                "1234567890",
                "0987654321",
                "john@doe.com"
            ),
            selectButton("Ok"),
            ProductScreen.goBackToMainScreen(),

            // Check searches
            ProductScreenPartnerList.searchCustomerValueAndClear("John Doe"),
            ProductScreenPartnerList.searchCustomerValueAndClear("1 street of astreet"),
            ProductScreenPartnerList.searchCustomerValueAndClear("26432685463"),
            ProductScreenPartnerList.searchCustomerValueAndClear("Acity"),
            ProductScreenPartnerList.searchCustomerValueAndClear("United States"),
            ProductScreenPartnerList.searchCustomerValueAndClear("1234567890"),
            ProductScreenPartnerList.searchCustomerValueAndClear("0987654321"),
            ProductScreen.clickPartnerButton(),
            PartnerList.searchCustomerValue("john@doe.com"),
        ].flat(),
});

registry.category("web_tour.tours").add("ParkOrderTour", {
    test: true,
    url: "/pos/ui",
    steps: () =>
        [
            Dialog.confirm("Open session"),

            ProductScreen.clickShowProductsMobile(),
            ProductScreen.clickDisplayedProduct("Test Product"),
            ProductScreen.clickReview(),
            ProductScreen.controlButtonMore(),
            ProductScreen.controlButton("Park Order"),
            refresh(),
            ProductScreen.orderIsEmpty(),
        ].flat(),
});
