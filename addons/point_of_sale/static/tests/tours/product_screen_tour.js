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
    negateStep,
} from "@point_of_sale/../tests/tours/utils/common";
import * as ProductConfiguratorPopup from "@point_of_sale/../tests/tours/utils/product_configurator_util";
import * as Numpad from "@point_of_sale/../tests/tours/utils/numpad_util";

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
            inLeftSide([
                ...ProductScreen.clickLine("Letter Tray"),
                ...ProductScreen.selectedOrderlineHasDirect("Letter Tray", "1.0"),
                Numpad.click("⌫"),
                ...ProductScreen.selectedOrderlineHasDirect("Letter Tray", "0.0", "0.0"),
                Numpad.click("⌫"),
                ...ProductScreen.selectedOrderlineHasDirect("Desk Organizer", "3.0", "15.30"),
                Numpad.click("⌫"),
                ...ProductScreen.selectedOrderlineHasDirect("Desk Organizer", "0.0", "0.0"),
                Numpad.click("1"),
                ...ProductScreen.selectedOrderlineHasDirect("Desk Organizer", "1.0", "5.10"),
                Numpad.click("2"),
                ...ProductScreen.selectedOrderlineHasDirect("Desk Organizer", "12.0", "61.2"),
                Numpad.click("3"),
                ...ProductScreen.selectedOrderlineHasDirect("Desk Organizer", "123.0", "627.3"),
                ...[".", "5"].map(Numpad.click),
                ...ProductScreen.selectedOrderlineHasDirect("Desk Organizer", "123.5", "629.85"),
            ]),
            // Check effects of numpad on product card quantity
            ProductScreen.productCardQtyIs("Desk Organizer", "123.5"),
            inLeftSide([
                // Re-select the order line after switching to the product screen
                { ...ProductScreen.clickLine("Desk Organizer", "123.5")[0], isActive: ["mobile"] },
                Numpad.click("Price"),
                Numpad.isActive("Price"),
                Numpad.click("1"),
                ...ProductScreen.selectedOrderlineHasDirect("Desk Organizer", "123.5", "123.5"),
                ...["1", "."].map(Numpad.click),
                ...ProductScreen.selectedOrderlineHasDirect("Desk Organizer", "123.5", "1,358.5"),
                Numpad.click("%"),
                Numpad.isActive("%"),
                ...["5", "."].map(Numpad.click),
                ...ProductScreen.selectedOrderlineHasDirect("Desk Organizer", "123.5", "1,290.58"),
                Numpad.click("Qty"),
                Numpad.isActive("Qty"),
                ...["⌫", "⌫"].map(Numpad.click),
                ...Order.doesNotHaveLine(),
            ]),
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
            inLeftSide([
                ...ProductScreen.clickLine("Whiteboard Pen"),
                Numpad.click("2"),
                ...ProductScreen.selectedOrderlineHasDirect("Whiteboard Pen", "2.0"),
                ...ProductScreen.clickLine("Wall Shelf Unit"),
                Numpad.click("2"),
                ...ProductScreen.selectedOrderlineHasDirect("Wall Shelf Unit", "2.0"),
                Numpad.click("⌫"),
                ...ProductScreen.selectedOrderlineHasDirect("Wall Shelf Unit", "0.0"),
                Numpad.click("⌫"),
                ...ProductScreen.selectedOrderlineHasDirect("Whiteboard Pen", "2.0"),
                Numpad.click("⌫"),
                ...ProductScreen.selectedOrderlineHasDirect("Whiteboard Pen", "0.0"),
                Numpad.click("⌫"),
                ...Order.doesNotHaveLine(),
            ]),

            // Add multiple orderlines then delete each of them until empty
            ProductScreen.clickDisplayedProduct("Whiteboard Pen"),
            ProductScreen.clickDisplayedProduct("Wall Shelf Unit"),
            ProductScreen.clickDisplayedProduct("Small Shelf"),
            ProductScreen.clickDisplayedProduct("Magnetic Board"),
            ProductScreen.clickDisplayedProduct("Monitor Stand"),
            inLeftSide([
                ...ProductScreen.clickLine("Whiteboard Pen"),
                Numpad.click("⌫"),
                ...ProductScreen.selectedOrderlineHasDirect("Whiteboard Pen", "0.0"),
                Numpad.click("⌫"),
                ...ProductScreen.selectedOrderlineHasDirect("Monitor Stand", "1.0"),
                ...ProductScreen.clickLine("Wall Shelf Unit"),
                Numpad.click("⌫"),
                ...ProductScreen.selectedOrderlineHasDirect("Wall Shelf Unit", "0.0"),
                Numpad.click("⌫"),
                ...ProductScreen.selectedOrderlineHasDirect("Monitor Stand", "1.0"),
                ...ProductScreen.clickLine("Small Shelf"),
                Numpad.click("⌫"),
                ...ProductScreen.selectedOrderlineHasDirect("Small Shelf", "0.0"),
                Numpad.click("⌫"),
                ...ProductScreen.selectedOrderlineHasDirect("Monitor Stand", "1.0"),
                ...ProductScreen.clickLine("Magnetic Board"),
                Numpad.click("⌫"),
                ...ProductScreen.selectedOrderlineHasDirect("Magnetic Board", "0.0"),
                Numpad.click("⌫"),
                ...ProductScreen.selectedOrderlineHasDirect("Monitor Stand", "1.0"),
                Numpad.click("⌫"),
                ...ProductScreen.selectedOrderlineHasDirect("Monitor Stand", "0.0"),
                Numpad.click("⌫"),
                ...Order.doesNotHaveLine(),
            ]),

            // Test OrderlineCustomerNoteButton
            ProductScreen.clickDisplayedProduct("Desk Organizer", true, "1.0"),
            inLeftSide([
                { ...ProductScreen.clickLine("Desk Organizer")[0], isActive: ["mobile"] },
                ...ProductScreen.addCustomerNote("Test customer note"),
                ...Order.hasLine({
                    productName: "Desk Organizer",
                    quantity: "1.0",
                    customerNote: "Test customer note",
                    withClass: ".selected",
                }),
            ]),
            ProductScreen.isShown(),

            // Test Cancel Order from Actions
            ProductScreen.clickReview(),
            ProductScreen.clickControlButton("Cancel Order"),
            Dialog.confirm(),
            { ...ProductScreen.back(), isActive: ["mobile"] },
            ProductScreen.orderIsEmpty(),
        ].flat(),
});

registry.category("web_tour.tours").add("FloatingOrderTour", {
    checkDelay: 50,
    steps: () =>
        [
            Chrome.startPoS(),
            ProductScreen.orderIsEmpty(),
            ProductScreen.clickDisplayedProduct("Desk Organizer", true, "1.0", "5.10"),
            ProductScreen.clickDisplayedProduct("Desk Organizer", true, "2.0", "10.20"),
            ProductScreen.productCardQtyIs("Desk Organizer", "2.0"),
            Chrome.createFloatingOrder(),
            ProductScreen.clickDisplayedProduct("Letter Tray", true, "1.0", "5.28"),
            ProductScreen.clickDisplayedProduct("Letter Tray", true, "2.0", "10.56"),
            ProductScreen.selectFloatingOrder(0),
            ProductScreen.productCardQtyIs("Desk Organizer", "2.0"),
            ProductScreen.isShown(),
            ProductScreen.selectFloatingOrder(1),
            ProductScreen.productCardQtyIs("Letter Tray", "2.0"),
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

registry.category("web_tour.tours").add("multiPricelistRulesTour", {
    checkDelay: 50,
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Test Product 1"),
            ProductScreen.selectedOrderlineHas("Test Product 1", "1.0", "200.0"),
            ProductScreen.clickDisplayedProduct("Test Product 1"),
            ProductScreen.selectedOrderlineHas("Test Product 1", "2.0", "200.0"), // 100.0 * 2
            ProductScreen.clickDisplayedProduct("Test Product 1"),
            ProductScreen.selectedOrderlineHas("Test Product 1", "3.0", "150.0"), // 50.0 * 3
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
            Dialog.confirm("Add"),

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
            inLeftSide([
                Numpad.click("5"),
                ...ProductScreen.selectedOrderlineHasDirect("Test Product", "5,00", "7.267,65"),
            ]),
            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("SearchProducts", {
    checkDelay: 50,
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.searchProduct("chair"),
            ProductScreen.clickDisplayedProduct("Test chair 1"),
            ProductScreen.clickDisplayedProduct("Test CHAIR 2"),
            ProductScreen.clickDisplayedProduct("Test sofa"),
            ProductScreen.searchProduct("CHAIR"),
            ProductScreen.clickDisplayedProduct("Test chair 1"),
            ProductScreen.clickDisplayedProduct("Test CHAIR 2"),
            ProductScreen.clickDisplayedProduct("Test sofa"),
            ProductScreen.searchProduct("clémentine"),
            ProductScreen.clickDisplayedProduct("clémentine"),
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
                "9898989899",
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
            ProductScreenPartnerList.searchCustomerValueAndClear("9898989899"),
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
            ProductScreen.productIsDisplayed("Product in AAB and AAX", 0),
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

registry.category("web_tour.tours").add("AutofillCashCount", {
    checkDelay: 50,
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Test Expensive"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.clickNextOrder(),
            ProductScreen.isShown(),
            Chrome.clickMenuOption("Close Register"),
            {
                trigger: ".fa-clone.btn-secondary",
                run: "click",
            },
            ProductScreen.cashDifferenceIs(0),
        ].flat(),
});

registry.category("web_tour.tours").add("ProductSearchTour", {
    checkDelay: 50,
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.searchProduct("Test Product"),
            ProductScreen.productIsDisplayed("Apple").map(negateStep),
            ProductScreen.productIsDisplayed("Test Product 1"),
            ProductScreen.productIsDisplayed("Test Product 2"),
            ProductScreen.searchProduct("Apple"),
            ProductScreen.productIsDisplayed("Test Product 1").map(negateStep),
            ProductScreen.productIsDisplayed("Test Product 2").map(negateStep),
            ProductScreen.searchProduct("Test Produt"), // typo to test the fuzzy search
            ProductScreen.productIsDisplayed("Test Product 1").map(negateStep),
            ProductScreen.productIsDisplayed("Test Product 2").map(negateStep),
            ProductScreen.searchProduct("1234567890123"),
            ProductScreen.productIsDisplayed("Test Product 2").map(negateStep),
            ProductScreen.productIsDisplayed("Test Product 1"),
            ProductScreen.searchProduct("1234567890124"),
            ProductScreen.productIsDisplayed("Test Product 1").map(negateStep),
            ProductScreen.productIsDisplayed("Test Product 2"),
            ProductScreen.searchProduct("TESTPROD1"),
            ProductScreen.productIsDisplayed("Test Product 2").map(negateStep),
            ProductScreen.productIsDisplayed("Test Product 1"),
            ProductScreen.searchProduct("TESTPROD2"),
            ProductScreen.productIsDisplayed("Test Product 1").map(negateStep),
            ProductScreen.productIsDisplayed("Test Product 2"),
        ].flat(),
});

registry.category("web_tour.tours").add("ProductCardUoMPrecision", {
    checkDelay: 50,
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Configurable Chair", false),
            ProductConfiguratorPopup.pickRadio("Leather"),
            Chrome.clickBtn("Add"),
            inLeftSide([
                Numpad.click("."),
                Numpad.click("1"),
                ...Order.hasLine({
                    productName: "Configurable Chair",
                    quantity: "0.1",
                }),
            ]),
            ProductScreen.clickDisplayedProduct("Configurable Chair", false),
            ProductConfiguratorPopup.pickRadio("wool"),
            Chrome.clickBtn("Add"),
            inLeftSide([
                Numpad.click("."),
                Numpad.click("7"),
                ...Order.hasLine({
                    productName: "Configurable Chair",
                    quantity: "0.7",
                }),
            ]),
            ProductScreen.productCardQtyIs("Configurable Chair", "0.8"),
            {
                content:
                    "Check the cart button if it shows the quantity in correct format/precision",
                isActive: ["mobile"],
                trigger: ".review-button:contains('0.8')",
            },
        ].flat(),
});

registry.category("web_tour.tours").add("AddMultipleSerialsAtOnce", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Product A"),
            ProductScreen.enterLotNumbers(["SN001", "SN002", "SN003"]),
            ProductScreen.selectedOrderlineHas("Product A", "3.0"),
            ProductScreen.clickDisplayedProduct("Product A"),
            [
                {
                    trigger: ".fa-trash-o",
                    run: "click",
                },
            ],
            ProductScreen.enterLotNumbers(["SN005", "SN006"]),
            ProductScreen.selectedOrderlineHas("Product A", "4.0"),
            Chrome.endTour(),
        ].flat(),
});
