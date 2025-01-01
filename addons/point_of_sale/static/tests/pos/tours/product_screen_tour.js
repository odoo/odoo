import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as PartnerList from "@point_of_sale/../tests/pos/tours/utils/partner_list_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as ProductScreenPartnerList from "@point_of_sale/../tests/pos/tours/utils/product_screen_partner_list_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as ReceiptScreen from "@point_of_sale/../tests/pos/tours/utils/receipt_screen_util";
import { registry } from "@web/core/registry";
import * as Order from "@point_of_sale/../tests/generic_helpers/order_widget_util";
import { back, inLeftSide, selectButton } from "@point_of_sale/../tests/pos/tours/utils/common";
import { scan_barcode, negateStep } from "@point_of_sale/../tests/generic_helpers/utils";
import * as ProductConfiguratorPopup from "@point_of_sale/../tests/pos/tours/utils/product_configurator_util";
import * as Numpad from "@point_of_sale/../tests/generic_helpers/numpad_util";
import * as OfflineUtil from "@point_of_sale/../tests/generic_helpers/offline_util";

registry.category("web_tour.tours").add("ProductScreenTour", {
    checkDelay: 50,
    steps: () =>
        [
            // Go by default to home category

            Chrome.startPoS(),
            OfflineUtil.setOfflineMode(),
            ProductScreen.firstProductIsFavorite("Whiteboard Pen"),
            ProductScreen.clickDisplayedProduct("Desk Organizer", true, "1", "5.10"),
            ProductScreen.clickDisplayedProduct("Desk Organizer", true, "2", "10.20"),
            ProductScreen.clickDisplayedProduct("Letter Tray", true, "1", "5.28"),
            ProductScreen.clickDisplayedProduct("Desk Organizer", true, "3", "15.30"),

            // Check effects of clicking numpad buttons
            inLeftSide([
                ...ProductScreen.clickLine("Letter Tray"),
                ...ProductScreen.selectedOrderlineHasDirect("Letter Tray", "1"),
                Numpad.click("⌫"),
                ...ProductScreen.selectedOrderlineHasDirect("Letter Tray", "0", "0.0"),
                Numpad.click("⌫"),
                ...ProductScreen.selectedOrderlineHasDirect("Desk Organizer", "3", "15.30"),
                Numpad.click("⌫"),
                ...ProductScreen.selectedOrderlineHasDirect("Desk Organizer", "0", "0.0"),
                Numpad.click("1"),
                ...ProductScreen.selectedOrderlineHasDirect("Desk Organizer", "1", "5.10"),
                Numpad.click("2"),
                ...ProductScreen.selectedOrderlineHasDirect("Desk Organizer", "12", "61.2"),
                Numpad.click("3"),
                ...ProductScreen.selectedOrderlineHasDirect("Desk Organizer", "123", "627.3"),
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
                ...ProductScreen.selectedOrderlineHasDirect("Whiteboard Pen", "2"),
                ...ProductScreen.clickLine("Wall Shelf Unit"),
                Numpad.click("2"),
                ...ProductScreen.selectedOrderlineHasDirect("Wall Shelf Unit", "2"),
                Numpad.click("⌫"),
                ...ProductScreen.selectedOrderlineHasDirect("Wall Shelf Unit", "0"),
                Numpad.click("⌫"),
                ...ProductScreen.selectedOrderlineHasDirect("Whiteboard Pen", "2"),
                Numpad.click("⌫"),
                ...ProductScreen.selectedOrderlineHasDirect("Whiteboard Pen", "0"),
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
                ...ProductScreen.selectedOrderlineHasDirect("Whiteboard Pen", "0"),
                Numpad.click("⌫"),
                ...ProductScreen.selectedOrderlineHasDirect("Monitor Stand", "1"),
                ...ProductScreen.clickLine("Wall Shelf Unit"),
                Numpad.click("⌫"),
                ...ProductScreen.selectedOrderlineHasDirect("Wall Shelf Unit", "0"),
                Numpad.click("⌫"),
                ...ProductScreen.selectedOrderlineHasDirect("Monitor Stand", "1"),
                ...ProductScreen.clickLine("Small Shelf"),
                Numpad.click("⌫"),
                ...ProductScreen.selectedOrderlineHasDirect("Small Shelf", "0"),
                Numpad.click("⌫"),
                ...ProductScreen.selectedOrderlineHasDirect("Monitor Stand", "1"),
                ...ProductScreen.clickLine("Magnetic Board"),
                Numpad.click("⌫"),
                ...ProductScreen.selectedOrderlineHasDirect("Magnetic Board", "0"),
                Numpad.click("⌫"),
                ...ProductScreen.selectedOrderlineHasDirect("Monitor Stand", "1"),
                Numpad.click("⌫"),
                ...ProductScreen.selectedOrderlineHasDirect("Monitor Stand", "0"),
                Numpad.click("⌫"),
                ...Order.doesNotHaveLine(),
            ]),

            // Test Customer notes
            ProductScreen.clickDisplayedProduct("Desk Organizer", true, "1"),
            inLeftSide([
                { ...ProductScreen.clickLine("Desk Organizer")[0], isActive: ["mobile"] },
                ...ProductScreen.addCustomerNote("Test customer note"),
                ...Order.hasLine({
                    productName: "Desk Organizer",
                    quantity: "1",
                    customerNote: "Test customer note",
                    withClass: ".selected",
                }),
                ...ProductScreen.clickSelectedLine("Desk Organizer"),
                ...ProductScreen.addCustomerNote("Test customer note on order"),
                ...Order.hasCustomerNote("Test customer note on order"),
            ]),

            // Test Internal notes
            inLeftSide([
                ...ProductScreen.clickLine("Desk Organizer"),
                ...ProductScreen.addInternalNote("Test internal note"),
                ...Order.hasLine({
                    productName: "Desk Organizer",
                    quantity: "1",
                    internalNote: "Test internal note",
                    withClass: ".selected",
                }),
                ...ProductScreen.clickSelectedLine("Desk Organizer"),
                ...ProductScreen.addInternalNote("Test internal note on order"),
                ...Order.hasInternalNote("Test internal note on order"),
            ]),
            ProductScreen.isShown(),
            OfflineUtil.setOnlineMode(),
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

            ProductScreen.clickDisplayedProduct("Test Product", true, "1", "100.0"),
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
            ProductScreen.selectedOrderlineHas("Test Product 1", "1", "80.0"),

            scan_barcode("0100201"),
            ProductScreen.selectedOrderlineHas("Test Product 2 (White)", "1", "100.0"),

            scan_barcode("0100202"),
            ProductScreen.selectedOrderlineHas("Test Product 2 (Red)", "1", "120.0"),

            scan_barcode("0100300"),
            ProductScreen.selectedOrderlineHas("Test Product 3", "1", "50.0"),
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
                ...ProductScreen.selectedOrderlineHasDirect("Test Product", "5", "7.267,65"),
            ]),
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
            ProductScreen.verifyCategorySequence(["AAA", "AAB", "AAC"]),
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
            ProductScreen.productIsDisplayed("Test Product 1"),
            ProductScreen.productIsDisplayed("Test Product 2"),
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
registry.category("web_tour.tours").add("SortOrderlinesByCategories", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            // Verify categories sequence
            ProductScreen.verifyCategorySequence(["Misc test", "Chair test"]),

            // Add products category wise
            ProductScreen.selectCategoryAndAddProduct("Misc test", "Product_1 Category sequence 1"),
            ProductScreen.selectCategoryAndAddProduct(
                "Chair test",
                "Product_11 Category sequence 2"
            ),
            ProductScreen.selectCategoryAndAddProduct("Misc test", "Product_2 Category sequence 1"),
            ProductScreen.selectCategoryAndAddProduct(
                "Chair test",
                "Product_22 Category sequence 2"
            ),

            ProductScreen.clickReview(),

            // Verify orderlines sequence
            ProductScreen.verifyOrderlineSequence([
                "Product_1 Category sequence 1",
                "Product_2 Category sequence 1",
                "Product_11 Category sequence 2",
                "Product_22 Category sequence 2",
            ]),
        ].flat(),
});
