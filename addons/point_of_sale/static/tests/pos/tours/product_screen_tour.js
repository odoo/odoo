/* global posmodel */

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
import { scan_barcode, negateStep, refresh } from "@point_of_sale/../tests/generic_helpers/utils";
import * as ProductConfiguratorPopup from "@point_of_sale/../tests/pos/tours/utils/product_configurator_util";
import * as Numpad from "@point_of_sale/../tests/generic_helpers/numpad_util";
import * as OfflineUtil from "@point_of_sale/../tests/generic_helpers/offline_util";
import * as TicketScreen from "@point_of_sale/../tests/pos/tours/utils/ticket_screen_util";
import * as Utils from "@point_of_sale/../tests/pos/tours/utils/common";
import * as BackendUtils from "@point_of_sale/../tests/pos/tours/utils/backend_utils";
import * as combo from "@point_of_sale/../tests/pos/tours/utils/combo_popup_util";
import { generatePreparationReceipts } from "@point_of_sale/../tests/pos/tours/utils/preparation_receipt_util";
import * as FeedbackScreen from "@point_of_sale/../tests/pos/tours/utils/feedback_screen_util";

registry.category("web_tour.tours").add("ProductScreenTour", {
    steps: () =>
        [
            // Go by default to home category

            Chrome.startPoS(),
            OfflineUtil.setOfflineMode(),
            ProductScreen.firstProductIsFavorite("Whiteboard Pen"),
            // Make sure we don't have any scroll bar on the product list
            {
                trigger: ".product-list",
                run: function () {
                    const productList = document.querySelector(".product-list");
                    if (productList.scrollWidth > document.documentElement.scrollWidth) {
                        throw new Error("Product list is overflowing");
                    }
                },
            },
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

registry.category("web_tour.tours").add("FloatingOrderTour", {
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
            {
                trigger: ".modal .btn-primary:contains(Proceed Anyway)",
                run: "click",
                expectUnloadPage: true,
            },
            {
                trigger: "button:contains(backend)",
                run: "click",
                expectUnloadPage: true,
            },
            {
                trigger: "body",
                expectUnloadPage: true,
            },
            ProductScreen.lastClosingCashIs("50.00"),
        ].flat(),
});

registry.category("web_tour.tours").add("ShowTaxExcludedTour", {
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
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            scan_barcode("0100100"),
            ProductScreen.selectedOrderlineHas("Test Product 1", "1", "80.0"),

            scan_barcode("0100201"),
            ProductScreen.selectedOrderlineHas("Test Product 2", "1", "100.0", "White"),

            scan_barcode("0100202"),
            ProductScreen.selectedOrderlineHas("Test Product 2", "1", "120.0", "Red"),

            refresh(),
            scan_barcode("0100100"),
            ProductScreen.selectedOrderlineHas("Test Product 1", "2", "160.0"),

            scan_barcode("0100300"),
            ProductScreen.selectedOrderlineHas("Test Product 3", "1", "50.0"),
            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_restricted_categories_combo_product", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.productIsDisplayed("Office Combo"),
            ProductScreen.productIsDisplayed("Combo Product 4"),
            ProductScreen.productIsDisplayed("Combo Product 5").map(negateStep),
            ProductScreen.clickDisplayedProduct("Office Combo"),
            combo.select("Combo Product 5"),
            Dialog.confirm(),
            {
                content: "Check if order preparation has product correctly ordered",
                trigger: "body",
                run: async () => {
                    const rendered = await generatePreparationReceipts();
                    if (!rendered[0].innerHTML.includes("Office Combo")) {
                        throw new Error("Office Combo not found in preparation receipt");
                    }
                    if (!rendered[0].innerHTML.includes("Combo Product 5")) {
                        throw new Error("Combo Product 5 not found in preparation receipt");
                    }
                },
            },
            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("MultiProductOptionsTour", {
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
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm(),
            ProductScreen.clickDisplayedProduct("Testez le produit"),
            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("DecimalCommaOrderlinePrice", {
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

registry.category("web_tour.tours").add("SearchProducts", {
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
            ProductScreen.searchProduct("2100005000000"),
            ProductScreen.clickDisplayedProduct("Wall Shelf Unit"),
        ].flat(),
});

registry.category("web_tour.tours").add("CheckProductInformation", {
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
            ProductScreen.clickInfoProduct("product_a", [
                {
                    trigger: ".section-financials :contains('Margin')",
                },
                Dialog.confirm("Close"),
            ]),
        ].flat(),
});

registry.category("web_tour.tours").add("PosCustomerAllFieldsDisplayed", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickPartnerButton(),
            PartnerList.checkContactValues(
                "John Doe",
                "1 street of astreet",
                "9898989899",
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
                trigger: '.category-button:eq(-1) > span:contains("AAX")',
            },
            {
                trigger: '.category-button:eq(-1) > span:contains("AAX")',
                run: "click",
            },
            {
                trigger: '.category-button:eq(-1) > span:contains("AAY")',
            },
        ].flat(),
});

registry.category("web_tour.tours").add("AutofillCashCount", {
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
            ProductScreen.searchProduct("Test Produt"),
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
registry.category("web_tour.tours").add("CustomerPopupTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickPartnerButton(),
            negateStep(PartnerList.checkCustomerShown("Z partner to search")),
            PartnerList.searchCustomerValue("Z partner to search", true),
            ProductScreen.clickCustomer("Z partner to search"),
            ProductScreen.clickPartnerButton(),
            negateStep(PartnerList.checkCustomerShown("Z partner to scroll")),
            PartnerList.scrollBottom(),
            ProductScreen.clickCustomer("Z partner to scroll"),
        ].flat(),
});

registry.category("web_tour.tours").add("test_pricelist_multi_items_different_qty_thresholds", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            ProductScreen.clickDisplayedProduct("tpmcapi product"),
            ProductScreen.clickDisplayedProduct("tpmcapi product"),
            ProductScreen.clickDisplayedProduct("tpmcapi product"),
            ProductScreen.clickPayButton(),
            PaymentScreen.totalIs("30"),
        ].flat(),
});

registry.category("web_tour.tours").add("ProductCardUoMPrecision", {
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

registry.category("web_tour.tours").add("test_pricelist_parent_category_rule", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Product with child category"),
            ProductScreen.selectedOrderlineHas("Product with child category", "1", "50.0"),
            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_product_create_update_from_frontend", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            Chrome.clickMenuOption("Create Product"),

            // Verify that the "New Product" dialog is displayed.
            Dialog.is({ title: "New Product" }),

            // Create a new product from frontend.
            ProductScreen.createProductFromFrontend(
                "Test Frontend Product",
                "710535977349",
                "20.0",
                "Chair test"
            ),
            Dialog.confirm(),
            {
                trigger: ".product-list article:contains(Test Frontend Product)",
            },

            // Click on the category button for "Chair test" to verify the product's addition.
            ProductScreen.clickSubcategory("Chair test"),
            ProductScreen.clickDisplayedProduct("Test Frontend Product"),
            inLeftSide([
                ...ProductScreen.selectedOrderlineHasDirect("Test Frontend Product", "1", "20.0"),
            ]),

            // Open the product's information popup.
            ProductScreen.clickInfoProduct(
                "Test Frontend Product",
                [
                    Dialog.confirm("Edit", ".btn-secondary"),
                    // Verify that the "Edit Product" dialog is displayed.
                    Dialog.is({ title: "Edit Product" }),

                    // Edit the product with new details.
                    ProductScreen.editProductFromFrontend(
                        "Test Frontend Product Edited",
                        "710535977348",
                        "50.0"
                    ),
                    Dialog.confirm(),
                ].flat()
            ),
            ProductScreen.clickSubcategory("Chair test"),
            ProductScreen.clickDisplayedProduct("Test Frontend Product Edited"),
            inLeftSide([
                ...ProductScreen.selectedOrderlineHasDirect(
                    "Test Frontend Product Edited",
                    "1",
                    "50.0"
                ),
            ]),
            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_draft_orders_not_syncing", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.orderIsEmpty(),
            ProductScreen.clickDisplayedProduct("Desk Pad"),
            Chrome.createFloatingOrder(),
            ProductScreen.clickDisplayedProduct("Desk Pad"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_fiscal_position_tax_group_labels", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Test Product"),
            ProductScreen.totalAmountIs("100.00"),
            ProductScreen.clickFiscalPosition("Fiscal Position Test"),
            ProductScreen.totalAmountIs("100.00"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank", true, { remaining: "0.00" }),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            {
                content: "Make sure orderline tax label is correct",
                trigger: ".orderline:contains('Tax Group 2')",
            },
            {
                content: "Make sure receipt tax label is correct and correspond to the orderline",
                trigger: ".pos-receipt-taxes:contains('Tax Group 2')",
            },
        ].flat(),
});

registry.category("web_tour.tours").add("test_one_attribute_value_scan_barcode", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            scan_barcode("1234567"),
            ProductScreen.selectedOrderlineHas("Product Test", "1.0", "10", "Large, Red"),

            scan_barcode("1234568"),
            ProductScreen.selectedOrderlineHas("Product Test", "1.0", "10", "Large, Blue"),

            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_product_long_press", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.longPressProduct("Test Product"),
            Dialog.is(),
            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_barcode_search_attributes_preset", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            // Step 1: Search and add first variant
            ProductScreen.searchProduct("12341357"),
            ProductScreen.productIsDisplayed("Product with Attributes", 0),
            ProductScreen.clickDisplayedProduct("Product with Attributes"),
            ProductScreen.selectedOrderlineHas(
                "Product with Attributes",
                "1.0",
                "10.0",
                "Value 1, Value 3, Value 5, Value 7"
            ),
            // Step 2: Search and add product without attributes (used to delay UI update)
            ProductScreen.searchProduct("987654321"),
            {
                content: "Wait for the product without attributes to be visible",
                trigger: '.product:contains("Product without Attributes")',
            },
            ProductScreen.clickDisplayedProduct("Product without Attributes"),
            ProductScreen.selectedOrderlineHas("Product without Attributes", "1.0"),

            // Step 3: Search and add second variant of the original product
            ProductScreen.searchProduct("123424689"),
            ProductScreen.productIsDisplayed("Product with Attributes", 0).map(negateStep),
            ProductScreen.searchProduct("12342468"),
            ProductScreen.productIsDisplayed("Product with Attributes", 0),
            ProductScreen.clickDisplayedProduct("Product with Attributes"),
            ProductScreen.selectedOrderlineHas(
                "Product with Attributes",
                "1.0",
                "10.0",
                "Value 2, Value 4, Value 6, Value 8"
            ),

            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_remove_archived_product_from_cache", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("A Test Product"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            Chrome.clickMenuOption("Close Register"),
            {
                trigger: ".modal .modal-footer .btn:contains(close register)",
                run: "click",
                expectUnloadPage: true,
            },
            {
                content: `Select button backend`,
                trigger: `button:contains(backend)`,
                run: "click",
                expectUnloadPage: true,
            },
            {
                trigger: "body",
                expectUnloadPage: true,
            },
            BackendUtils.openProductForm("A Test Product"),
            {
                trigger: `.fa-cog`,
                run: "click",
            },
            {
                trigger: ".dropdown-item:contains('Archive')",
                run: "click",
            },
            Utils.selectButton("Archive"),
            BackendUtils.openShopSession("Shop"),
            Dialog.confirm("Open Register"),
            ProductScreen.productIsDisplayed("A Test Product").map(negateStep),
        ].flat(),
});

registry.category("web_tour.tours").add("test_preset_timing_retail", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            ProductScreen.selectPreset("Dine in", "Delivery"),
            PartnerList.clickPartner("A simple PoS man!"),
            Chrome.selectPresetTimingSlotHour("15:00"),
            Chrome.presetTimingSlotIs("15:00"),
            Chrome.createFloatingOrder(),
            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            Chrome.clickOrders(),
            TicketScreen.nthRowContains(1, "A simple PoS man!"),
            TicketScreen.nthRowContains(1, "Delivery", false),
            TicketScreen.nthRowContains(2, "002"),
            TicketScreen.nthRowContains(2, "Dine in", false),
        ].flat(),
});

registry
    .category("web_tour.tours")
    .add("test_fast_payment_validation_from_product_screen_without_automatic_receipt_printing", {
        steps: () =>
            [
                Chrome.startPoS(),
                Dialog.confirm("Open Register"),
                ProductScreen.clickDisplayedProduct("Desk Organizer"),
                ProductScreen.clickFastPaymentButton("Bank"),
                ReceiptScreen.isShown(),
                ReceiptScreen.clickNextOrder(),
                ProductScreen.clickDisplayedProduct("Desk Organizer"),
                ProductScreen.clickPayButton(),
                PaymentScreen.clickPaymentMethod("Bank"),
                PaymentScreen.clickValidate(),
                ReceiptScreen.isShown(),
            ].flat(),
    });

registry
    .category("web_tour.tours")
    .add("test_fast_payment_validation_from_product_screen_with_automatic_receipt_printing", {
        steps: () =>
            [
                Chrome.startPoS(),
                Dialog.confirm("Open Register"),
                ProductScreen.clickDisplayedProduct("Desk Organizer"),
                ProductScreen.clickFastPaymentButton("Bank"),
                FeedbackScreen.isShown(),
                Dialog.confirm(),
                FeedbackScreen.clickScreen(),
                ProductScreen.isShown(),
                ProductScreen.clickDisplayedProduct("Desk Organizer"),
                ProductScreen.clickPayButton(),
                PaymentScreen.clickPaymentMethod("Bank"),
                PaymentScreen.clickValidate(),
                FeedbackScreen.isShown(),
                Dialog.confirm(),
                FeedbackScreen.clickScreen(),
                ProductScreen.isShown(),
            ].flat(),
    });

registry.category("web_tour.tours").add("test_only_existing_lots", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Product with existing lots"),
            ProductScreen.selectNthLotNumber(1),
            ProductScreen.selectedOrderlineHas("Product with existing lots", "1.0"),
            inLeftSide({
                trigger: ".order-container .orderline .lot-number:contains('Lot Number 1001')",
            }),
            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_delete_line", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            {
                content: "replace disallowLineQuantityChange to be true",
                trigger: "body",
                run: () => {
                    posmodel.disallowLineQuantityChange = () => true;
                },
            },
            inLeftSide([
                ...ProductScreen.selectedOrderlineHasDirect("Desk Organizer", "1"),
                Numpad.click("⌫"),
                {
                    content: "Click 0",
                    trigger: ".modal " + Numpad.buttonTriger("0"),
                    run: "click",
                },
                ...Chrome.confirmPopup(),
                ...ProductScreen.selectedOrderlineHasDirect("Desk Organizer", "0"),
                Numpad.click("⌫"),
                {
                    content: "Click 0",
                    trigger: ".modal " + Numpad.buttonTriger("0"),
                    run: "click",
                },
                ...Chrome.confirmPopup(),
            ]),
            ProductScreen.orderIsEmpty(),
            Chrome.endTour(),
        ].flat(),
});

function clickLoadSampleButton() {
    return [
        {
            trigger:
                '.o_view_nocontent .o_nocontent_help button.btn-primary:contains("Load Sample")',
            content: "Click on Load Sample button",
            run: "click",
        },
    ].flat();
}

registry.category("web_tour.tours").add("test_load_pos_demo_data_by_pos_user", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            clickLoadSampleButton(),
            {
                trigger:
                    '.modal-content:has(.modal-title:contains("Access Denied")) .modal-footer .btn.btn-primary:contains("Ok")',
                content: "Click Ok on the Access Denied dialog box",
                run: "click",
            },
            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_pos_ui_round_globally", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Test Product 1"),
            ProductScreen.clickDisplayedProduct("Test Product 2"),
            inLeftSide([
                ...["+/-"].map(Numpad.click),
                ...ProductScreen.selectedOrderlineHasDirect("Test Product 2", "-1.0"),
            ]),
            ProductScreen.totalAmountIs("7,771.01"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            Chrome.endTour(),
        ].flat(),
});
