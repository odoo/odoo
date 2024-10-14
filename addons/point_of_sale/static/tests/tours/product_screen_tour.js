import * as PaymentScreen from "@point_of_sale/../tests/tours/utils/payment_screen_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import * as PartnerList from "@point_of_sale/../tests/tours/utils/partner_list_util";
import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as ProductScreenPartnerList from "@point_of_sale/../tests/tours/utils/product_screen_partner_list_util";
import * as Chrome from "@point_of_sale/../tests/tours/utils/chrome_util";
import * as ReceiptScreen from "@point_of_sale/../tests/tours/utils/receipt_screen_util";
import { registry } from "@web/core/registry";
import * as Order from "@point_of_sale/../tests/tours/utils/generic_components/order_widget_util";
import {
    back,
    inLeftSide,
    selectButton,
    scan_barcode,
} from "@point_of_sale/../tests/tours/utils/common";
import * as ProductConfiguratorPopup from "@point_of_sale/../tests/tours/utils/product_configurator_util";

registry.category("web_tour.tours").add("ProductScreenTour", {
    checkDelay: 50,
    steps: () =>
        [
            // Go by default to home category

            Chrome.startPoS(),
            ProductScreen.clickDisplayedProduct("Desk Organizer", true, "1.0", "5.10"),
            ProductScreen.clickDisplayedProduct("Desk Organizer", true, "2.0", "10.20"),
            ProductScreen.clickDisplayedProduct("Letter Tray", true, "1.0", "5.28"),
            ProductScreen.clickDisplayedProduct("Desk Organizer", true, "3.0", "15.30"),

            // Check effects of clicking numpad buttons
            ProductScreen.clickOrderline("Letter Tray", "1"),
            ProductScreen.selectedOrderlineHas("Letter Tray", "1.0"),
            ProductScreen.clickNumpad("⌫"),
            ProductScreen.selectedOrderlineHas("Letter Tray", "0.0", "0.0"),
            ProductScreen.clickNumpad("⌫"),
            ProductScreen.selectedOrderlineHas("Desk Organizer", "3", "15.30"),
            ProductScreen.clickNumpad("⌫"),
            ProductScreen.selectedOrderlineHas("Desk Organizer", "0.0", "0.0"),
            ProductScreen.clickNumpad("1"),
            ProductScreen.selectedOrderlineHas("Desk Organizer", "1.0", "5.1"),
            ProductScreen.clickNumpad("2"),
            ProductScreen.selectedOrderlineHas("Desk Organizer", "12.0", "61.2"),
            ProductScreen.clickNumpad("3"),
            ProductScreen.selectedOrderlineHas("Desk Organizer", "123.0", "627.3"),
            ProductScreen.clickNumpad(".", "5"),
            ProductScreen.selectedOrderlineHas("Desk Organizer", "123.5", "629.85"),
            ProductScreen.clickNumpad("Price"),
            ProductScreen.modeIsActive("Price"),
            ProductScreen.clickNumpad("1"),
            ProductScreen.selectedOrderlineHas("Desk Organizer", "123.5", "123.5"),
            ProductScreen.clickNumpad("1", "."),
            ProductScreen.selectedOrderlineHas("Desk Organizer", "123.5", "1,358.5"),
            ProductScreen.clickNumpad("%"),
            ProductScreen.modeIsActive("%"),
            ProductScreen.clickNumpad("5", "."),
            ProductScreen.selectedOrderlineHas("Desk Organizer", "123.5", "1,290.58"),
            ProductScreen.clickNumpad("Qty"),
            ProductScreen.clickNumpad("⌫"),
            ProductScreen.clickNumpad("⌫"),
            ProductScreen.orderIsEmpty(),

            // Check different subcategories
            ProductScreen.clickSubcategory("Desk test"),
            ProductScreen.productIsDisplayed("Desk Pad"),
            ProductScreen.clickSubcategory("Misc test"),
            ProductScreen.productIsDisplayed("Whiteboard Pen"),
            ProductScreen.clickSubcategory("Chair test"),
            ProductScreen.productIsDisplayed("Letter Tray"),
            ProductScreen.clickSubcategory("Chair test"),

            // Add two orderlines and update quantity
            ProductScreen.clickDisplayedProduct("Whiteboard Pen"),
            ProductScreen.clickDisplayedProduct("Wall Shelf Unit"),
            ProductScreen.clickOrderline("Whiteboard Pen", "1.0"),
            ProductScreen.clickNumpad("2"),
            ProductScreen.selectedOrderlineHas("Whiteboard Pen", "2.0"),
            ProductScreen.clickOrderline("Wall Shelf Unit", "1.0"),
            ProductScreen.clickNumpad("2"),
            ProductScreen.selectedOrderlineHas("Wall Shelf Unit", "2.0"),
            ProductScreen.clickNumpad("⌫"),
            ProductScreen.selectedOrderlineHas("Wall Shelf Unit", "0.0"),
            ProductScreen.clickNumpad("⌫"),
            ProductScreen.selectedOrderlineHas("Whiteboard Pen", "2.0"),
            ProductScreen.clickNumpad("⌫"),
            ProductScreen.selectedOrderlineHas("Whiteboard Pen", "0.0"),
            ProductScreen.clickNumpad("⌫"),
            ProductScreen.orderIsEmpty(),

            // Add multiple orderlines then delete each of them until empty
            ProductScreen.clickDisplayedProduct("Whiteboard Pen"),
            ProductScreen.clickDisplayedProduct("Wall Shelf Unit"),
            ProductScreen.clickDisplayedProduct("Small Shelf"),
            ProductScreen.clickDisplayedProduct("Magnetic Board"),
            ProductScreen.clickDisplayedProduct("Monitor Stand"),
            ProductScreen.clickOrderline("Whiteboard Pen", "1.0"),
            ProductScreen.clickNumpad("⌫"),
            ProductScreen.selectedOrderlineHas("Whiteboard Pen", "0.0"),
            ProductScreen.clickNumpad("⌫"),
            ProductScreen.selectedOrderlineHas("Monitor Stand", "1.0"),
            ProductScreen.clickOrderline("Wall Shelf Unit", "1.0"),
            ProductScreen.clickNumpad("⌫"),
            ProductScreen.selectedOrderlineHas("Wall Shelf Unit", "0.0"),
            ProductScreen.clickNumpad("⌫"),
            ProductScreen.selectedOrderlineHas("Monitor Stand", "1.0"),
            ProductScreen.clickOrderline("Small Shelf", "1.0"),
            ProductScreen.clickNumpad("⌫"),
            ProductScreen.selectedOrderlineHas("Small Shelf", "0.0"),
            ProductScreen.clickNumpad("⌫"),
            ProductScreen.selectedOrderlineHas("Monitor Stand", "1.0"),
            ProductScreen.clickOrderline("Magnetic Board", "1.0"),
            ProductScreen.clickNumpad("⌫"),
            ProductScreen.selectedOrderlineHas("Magnetic Board", "0.0"),
            ProductScreen.clickNumpad("⌫"),
            ProductScreen.selectedOrderlineHas("Monitor Stand", "1.0"),
            ProductScreen.clickNumpad("⌫"),
            ProductScreen.selectedOrderlineHas("Monitor Stand", "0.0"),
            ProductScreen.clickNumpad("⌫"),
            ProductScreen.orderIsEmpty(),

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
    checkDelay: 50,
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Test Product"),
            ProductScreen.totalAmountIs("100.00"),
            ProductScreen.clickFiscalPosition("No Tax"),
            ProductScreen.totalAmountIs("100.00"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank", true, { remaining: "0.00" }),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            Order.doesNotHaveLine({ discount: "" }),
        ].flat(),
});

registry.category("web_tour.tours").add("FiscalPositionIncl", {
    checkDelay: 50,
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Test Product 1"),
            ProductScreen.totalAmountIs("100.00"),
            ProductScreen.clickFiscalPosition("Incl. to Incl."),
            ProductScreen.totalAmountIs("100.00"),
            // changed fiscal position to Incl. to Excl.
            ProductScreen.clickFiscalPosition("Incl. to Excl."),
            ProductScreen.totalAmountIs("110.00"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank", true, { remaining: "0.00" }),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            ReceiptScreen.clickNextOrder(),
        ].flat(),
});

registry.category("web_tour.tours").add("FiscalPositionExcl", {
    checkDelay: 50,
    steps: () =>
        [
            Chrome.startPoS(),
            ProductScreen.clickDisplayedProduct("Test Product 2"),
            ProductScreen.totalAmountIs("120.00"),
            ProductScreen.clickFiscalPosition("Excl. to Excl."),
            ProductScreen.totalAmountIs("110.00"),
            // changed fiscal position to Excl. to Incl.
            ProductScreen.clickFiscalPosition("Excl. to Incl."),
            ProductScreen.totalAmountIs("100.00"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank", true, { remaining: "0.00" }),
            PaymentScreen.clickValidate(),
        ].flat(),
});

registry.category("web_tour.tours").add("CashClosingDetails", {
    checkDelay: 50,
    steps: () =>
        [
            Chrome.startPoS(),
            ProductScreen.enterOpeningAmount("0"),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("Desk Organizer", "10"), //5.1 per item
            ProductScreen.totalAmountIs("51.00"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.remainingIs("0.0"),
            PaymentScreen.clickValidate(),
            Chrome.clickMenuOption("Close Register"),
            ProductScreen.closeWithCashAmount("50.0"),
            ProductScreen.cashDifferenceIs("-1.00"),
            Dialog.confirm("Close Register"),
            Dialog.confirm("Proceed Anyway", ".btn-primary"),
            Chrome.clickBtn("Backend"),
            ProductScreen.lastClosingCashIs("50.00"),
        ].flat(),
});

registry.category("web_tour.tours").add("ShowTaxExcludedTour", {
    checkDelay: 50,
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            ProductScreen.clickDisplayedProduct("Test Product", true, "1.0", "100.0"),
            ProductScreen.totalAmountIs("110.0"),
            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("limitedProductPricelistLoading", {
    checkDelay: 50,
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

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
    checkDelay: 50,
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            ProductScreen.clickDisplayedProduct("Product A"),
            ProductConfiguratorPopup.isOptionShown("Value 1"),
            ProductConfiguratorPopup.isOptionShown("Value 2"),
            Dialog.confirm("Ok"),

            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("TranslateProductNameTour", {
    checkDelay: 50,
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm(),
            ProductScreen.clickDisplayedProduct("Testez le produit"),
            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("DecimalCommaOrderlinePrice", {
    checkDelay: 50,
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Test Product"),
            ProductScreen.clickNumpad("5"),
            ProductScreen.selectedOrderlineHas("Test Product", "5,00", "7.267,65"),
            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("CheckProductInformation", {
    checkDelay: 50,
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            // Check that the product form is shown.
            Chrome.clickMenuButton(),
            Chrome.clickMenuDropdownOption("Create Product"),
            Dialog.is({ title: "New Product" }),
            Dialog.cancel(),

            // Check margin on a product.
            ProductScreen.clickInfoProduct("product_a"),
            {
                trigger: ".section-financials :contains('Margin')",
            },
            {
                trigger: ".section-product-info-title:not(:contains('On hand:'))",
                run: () => {},
            },
        ].flat(),
});

registry.category("web_tour.tours").add("PosCustomerAllFieldsDisplayed", {
    checkDelay: 50,
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickPartnerButton(),
            PartnerList.checkContactValues(
                "John Doe",
                "1 street of astreet",
                "1234567890",
                "0987654321",
                "john@doe.com"
            ),
            selectButton("Discard"),
            {
                isActive: ["mobile"],
                ...back(),
            },

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

registry.category("web_tour.tours").add("PosCategoriesOrder", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            {
                trigger: '.category-button:eq(0) > span:contains("AAA")',
            },
            {
                trigger: '.category-button:eq(1) > span:contains("AAB")',
            },
            {
                trigger: '.category-button:eq(2) > span:contains("AAC")',
            },
            {
                trigger: '.category-button:eq(1) > span:contains("AAB")',
                run: "click",
            },
            {
                trigger: '.category-button:eq(2) > span:contains("AAX")',
            },
            {
                trigger: '.category-button:eq(2) > span:contains("AAX")',
                run: "click",
            },
            {
                trigger: '.category-button:eq(3) > span:contains("AAY")',
            },
        ].flat(),
});
