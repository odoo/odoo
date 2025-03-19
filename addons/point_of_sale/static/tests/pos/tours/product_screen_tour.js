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
            Chrome.startPoS(),
            OfflineUtil.setOfflineMode(),
            ProductScreen.firstProductIsFavorite("Awesome Article"),
            ProductScreen.clickDisplayedProduct("Awesome Thing", true, "1", "5.10"),
            ProductScreen.clickDisplayedProduct("Awesome Thing", true, "2", "10.20"),
            ProductScreen.clickDisplayedProduct("Product for pricelist 6", true, "1", "5.28"),
            ProductScreen.clickDisplayedProduct("Awesome Thing", true, "3", "15.30"),

            // Check effects of clicking numpad buttons
            inLeftSide([
                ...ProductScreen.clickLine("Product for pricelist 6"),
                ...ProductScreen.selectedOrderlineHasDirect("Product for pricelist 6", "1"),
                Numpad.click("⌫"),
                ...ProductScreen.selectedOrderlineHasDirect("Product for pricelist 6", "0", "0.0"),
                Numpad.click("⌫"),
                ...ProductScreen.selectedOrderlineHasDirect("Awesome Thing", "3", "15.30"),
                Numpad.click("⌫"),
                ...ProductScreen.selectedOrderlineHasDirect("Awesome Thing", "0", "0.0"),
                Numpad.click("1"),
                ...ProductScreen.selectedOrderlineHasDirect("Awesome Thing", "1", "5.10"),
                Numpad.click("2"),
                ...ProductScreen.selectedOrderlineHasDirect("Awesome Thing", "12", "61.2"),
                Numpad.click("3"),
                ...ProductScreen.selectedOrderlineHasDirect("Awesome Thing", "123", "627.3"),
                ...[".", "5"].map(Numpad.click),
                ...ProductScreen.selectedOrderlineHasDirect("Awesome Thing", "123.5", "629.85"),
            ]),
            // Check effects of numpad on product card quantity
            ProductScreen.productCardQtyIs("Awesome Thing", "123.5"),
            inLeftSide([
                // Re-select the order line after switching to the product screen
                { ...ProductScreen.clickLine("Awesome Thing", "123.5")[0], isActive: ["mobile"] },
                Numpad.click("Price"),
                Numpad.isActive("Price"),
                Numpad.click("1"),
                ...ProductScreen.selectedOrderlineHasDirect("Awesome Thing", "123.5", "123.5"),
                ...["1", "."].map(Numpad.click),
                ...ProductScreen.selectedOrderlineHasDirect("Awesome Thing", "123.5", "1,358.5"),
                Numpad.click("%"),
                Numpad.isActive("%"),
                ...["5", "."].map(Numpad.click),
                ...ProductScreen.selectedOrderlineHasDirect("Awesome Thing", "123.5", "1,290.58"),
                Numpad.click("Qty"),
                Numpad.isActive("Qty"),
                ...["⌫", "⌫"].map(Numpad.click),
                ...Order.doesNotHaveLine(),
            ]),
            // Check different subcategories
            ProductScreen.clickSubcategory("Things"),
            ProductScreen.productIsDisplayed("Awesome Thing"),
            ProductScreen.clickSubcategory("Items"),
            ProductScreen.productIsDisplayed("Awesome Item"),
            ProductScreen.clickSubcategory("Article"),
            ProductScreen.productIsDisplayed("Awesome Article"),
            ProductScreen.clickSubcategory("Article"),

            // Add two orderlines and update quantity
            ProductScreen.clickDisplayedProduct("Awesome Article"),
            ProductScreen.clickDisplayedProduct("Awesome Item"),
            inLeftSide([
                ...ProductScreen.clickLine("Awesome Article"),
                Numpad.click("2"),
                ...ProductScreen.selectedOrderlineHasDirect("Awesome Article", "2"),
                ...ProductScreen.clickLine("Awesome Item"),
                Numpad.click("2"),
                ...ProductScreen.selectedOrderlineHasDirect("Awesome Item", "2"),
                Numpad.click("⌫"),
                ...ProductScreen.selectedOrderlineHasDirect("Awesome Item", "0"),
                Numpad.click("⌫"),
                ...ProductScreen.selectedOrderlineHasDirect("Awesome Article", "2"),
                Numpad.click("⌫"),
                ...ProductScreen.selectedOrderlineHasDirect("Awesome Article", "0"),
                Numpad.click("⌫"),
                ...Order.doesNotHaveLine(),
            ]),

            // Add multiple orderlines then delete each of them until empty
            ProductScreen.clickDisplayedProduct("Awesome Thing"),
            ProductScreen.clickDisplayedProduct("Awesome Item"),
            ProductScreen.clickDisplayedProduct("Product for pricelist 2"),
            ProductScreen.clickDisplayedProduct("Product for pricelist 3"),
            ProductScreen.clickDisplayedProduct("Product for pricelist 4"),
            inLeftSide([
                ...ProductScreen.clickLine("Awesome Thing"),
                Numpad.click("⌫"),
                ...ProductScreen.selectedOrderlineHasDirect("Awesome Thing", "0"),
                Numpad.click("⌫"),
                ...ProductScreen.selectedOrderlineHasDirect("Product for pricelist 4", "1"),
                ...ProductScreen.clickLine("Awesome Item"),
                Numpad.click("⌫"),
                ...ProductScreen.selectedOrderlineHasDirect("Awesome Item", "0"),
                Numpad.click("⌫"),
                ...ProductScreen.selectedOrderlineHasDirect("Product for pricelist 4", "1"),
                ...ProductScreen.clickLine("Product for pricelist 2"),
                Numpad.click("⌫"),
                ...ProductScreen.selectedOrderlineHasDirect("Product for pricelist 2", "0"),
                Numpad.click("⌫"),
                ...ProductScreen.selectedOrderlineHasDirect("Product for pricelist 4", "1"),
                ...ProductScreen.clickLine("Product for pricelist 3"),
                Numpad.click("⌫"),
                ...ProductScreen.selectedOrderlineHasDirect("Product for pricelist 3", "0"),
                Numpad.click("⌫"),
                ...ProductScreen.selectedOrderlineHasDirect("Product for pricelist 4", "1"),
                Numpad.click("⌫"),
                ...ProductScreen.selectedOrderlineHasDirect("Product for pricelist 4", "0"),
                Numpad.click("⌫"),
                ...Order.doesNotHaveLine(),
            ]),

            // Test Customer notes
            ProductScreen.clickDisplayedProduct("Awesome Thing", true, "1"),
            inLeftSide([
                { ...ProductScreen.clickLine("Awesome Thing")[0], isActive: ["mobile"] },
                ...ProductScreen.addCustomerNote("Test customer note"),
                ...Order.hasLine({
                    productName: "Awesome Thing",
                    quantity: "1",
                    customerNote: "Test customer note",
                    withClass: ".selected",
                }),
                ...ProductScreen.clickSelectedLine("Awesome Thing"),
                ...ProductScreen.addCustomerNote("Test customer note on order"),
                ...Order.hasCustomerNote("Test customer note on order"),
            ]),

            // Test Internal notes
            inLeftSide([
                ...ProductScreen.clickLine("Awesome Thing"),
                ...ProductScreen.addInternalNote("Test internal note"),
                ...Order.hasLine({
                    productName: "Awesome Thing",
                    quantity: "1",
                    internalNote: "Test internal note",
                    withClass: ".selected",
                }),
                ...ProductScreen.clickSelectedLine("Awesome Thing"),
                ...ProductScreen.addInternalNote("Test internal note on order"),
                ...Order.hasInternalNote("Test internal note on order"),
            ]),
            ProductScreen.isShown(),
            OfflineUtil.setOnlineMode(),
        ].flat(),
});

registry.category("web_tour.tours").add("FloatingOrderTour", {
    checkDelay: 50,
    steps: () =>
        [
            Chrome.startPoS(),
            ProductScreen.orderIsEmpty(),
            ProductScreen.clickDisplayedProduct("Awesome Thing", true, "1.0", "5.10"),
            ProductScreen.clickDisplayedProduct("Awesome Thing", true, "2.0", "10.20"),
            ProductScreen.productCardQtyIs("Awesome Thing", "2.0"),
            Chrome.createFloatingOrder(),
            ProductScreen.clickDisplayedProduct("Product for pricelist 6", true, "1.0", "5.28"),
            ProductScreen.clickDisplayedProduct("Product for pricelist 6", true, "2.0", "10.56"),
            ProductScreen.selectFloatingOrder(0),
            ProductScreen.productCardQtyIs("Awesome Thing", "2.0"),
            ProductScreen.isShown(),
            ProductScreen.selectFloatingOrder(1),
            ProductScreen.productCardQtyIs("Product for pricelist 6", "2.0"),
        ].flat(),
});

registry.category("web_tour.tours").add("FiscalPositionNoTax", {
    checkDelay: 50,
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Taxed Product"),
            ProductScreen.totalAmountIs("100.00"),
            ProductScreen.clickFiscalPosition("FP-POS-2M"),
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
            ProductScreen.clickDisplayedProduct("Awesome Item"),
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
            ProductScreen.clickDisplayedProduct("Awesome Article"),
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
            ProductScreen.addOrderline("Awesome Thing", "10"), //5.1 per item
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
            ProductScreen.clickDisplayedProduct("Taxed Product", true, "1", "86.96"),
            ProductScreen.totalAmountIs("100.0"),
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
            ProductScreen.selectedOrderlineHas("Product for pricelist 1", "1", "80.0"),

            scan_barcode("0100201"),
            ProductScreen.selectedOrderlineHas("Configurable 1", "1", "50.0", "Red"),

            scan_barcode("0100202"),
            ProductScreen.selectedOrderlineHas("Configurable 1", "1", "120.0", "Blue"),

            scan_barcode("0100300"),
            ProductScreen.selectedOrderlineHas("Product for pricelist 2", "1", "100.0"),
            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("MultiProductOptionsTour", {
    checkDelay: 50,
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            ProductScreen.clickDisplayedProduct("Configurable Multi"),
            ProductConfiguratorPopup.isOptionShown("Multi 1"),
            ProductConfiguratorPopup.isOptionShown("Multi 2"),
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
            ProductScreen.clickDisplayedProduct("Magnifique Produit"),
            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("DecimalCommaOrderlinePrice", {
    checkDelay: 50,
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Awesome Item"),
            inLeftSide([
                Numpad.click("5"),
                ...ProductScreen.selectedOrderlineHasDirect("Awesome Item", "5", "7.267,65"),
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
            ProductScreen.searchProduct("2100005000000"),
            ProductScreen.clickDisplayedProduct("Awesome Item"),
        ].flat(),
});

registry.category("web_tour.tours").add("CheckProductInformation", {
    checkDelay: 50,
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            Chrome.clickMenuButton(),
            Chrome.clickMenuDropdownOption("Create Product"),
            Dialog.is({ title: "New Product" }),
            Dialog.cancel(),
            ProductScreen.clickInfoProduct("Awesome Thing"),
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
