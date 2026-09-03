/* global posmodel */

import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as PartnerList from "@point_of_sale/../tests/pos/tours/utils/partner_list_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import { registry } from "@web/core/registry";
import * as Order from "@point_of_sale/../tests/generic_helpers/order_widget_util";
import { inLeftSide } from "@point_of_sale/../tests/pos/tours/utils/common";
import { scan_barcode, negateStep, refresh } from "@point_of_sale/../tests/generic_helpers/utils";
import * as ProductConfiguratorPopup from "@point_of_sale/../tests/pos/tours/utils/product_configurator_util";
import * as Numpad from "@point_of_sale/../tests/generic_helpers/numpad_util";
import * as OfflineUtil from "@point_of_sale/../tests/generic_helpers/offline_util";
import * as TicketScreen from "@point_of_sale/../tests/pos/tours/utils/ticket_screen_util";
import * as combo from "@point_of_sale/../tests/pos/tours/utils/combo_popup_util";
import * as Utils from "@point_of_sale/../tests/pos/tours/utils/common";
import * as BackendUtils from "@point_of_sale/../tests/pos/tours/utils/backend_utils";
import * as FeedbackScreen from "@point_of_sale/../tests/pos/tours/utils/feedback_screen_util";
import { delay } from "@web/core/utils/concurrency";

registry.category("web_tour.tours").add("ProductScreenTour", {
    steps: () =>
        [
            // Go by default to home category

            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            OfflineUtil.setOfflineMode(),
            inLeftSide([
                ...ProductScreen.clickControlButtonMore(),
                // check that cancel order button is disabled if there is no orderline in the order
                {
                    content: "Check that cancel order button is disabled",
                    trigger: ".control-buttons button:contains('Cancel Order'):disabled",
                },
                Dialog.cancel(),
            ]),
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

registry.category("web_tour.tours").add("test_reuse_empty_floating_order", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.orderIsEmpty(),
            ProductScreen.checkFloatingOrderCount(1),
            ProductScreen.clickDisplayedProduct("Desk Organizer", true, "1.0", "5.10"),
            Chrome.createFloatingOrder(),
            ProductScreen.checkFloatingOrderCount(2),
            ProductScreen.selectFloatingOrder(0),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank", true, { remaining: "0.00" }),
            PaymentScreen.clickValidate(),
            FeedbackScreen.isShown(),
            FeedbackScreen.clickNextOrder(),
            // Should reuse previously created empty floating order
            ProductScreen.checkFloatingOrderCount(1),
        ].flat(),
});

registry.category("web_tour.tours").add("CashClosingDetails", {
    steps: () =>
        [
            Chrome.startPoS(),
            ProductScreen.enterOpeningAmount("0"),
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
        ].flat(),
});

registry.category("web_tour.tours").add("limitedProductPricelistLoading", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            scan_barcode("0100100"),
            ProductScreen.selectedOrderlineHas("Test Product 1", "1", "80.0"),
            ProductScreen.totalAmountIs("80.0"),

            refresh(),
            inLeftSide([
                ...ProductScreen.clickLine("Test Product 1"),
                ...ProductScreen.selectedOrderlineHasDirect("Test Product 1", "1"),
                Numpad.click("2"),
                ...ProductScreen.selectedOrderlineHasDirect("Test Product 1", "2", "140.0"),
            ]),
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
            ProductScreen.searchProduct("galaxy"),
            ProductScreen.productIsDisplayed("galaxy"),
            ProductScreen.productIsDisplayed("Test Product variant"),
            ProductScreen.searchProduct("galaxy variant"),
            ProductScreen.productIsDisplayed("galaxy").map(negateStep),
            ProductScreen.productIsDisplayed("Test Product variant"),
            ProductScreen.searchProduct("1234567890123"),
            ProductScreen.productIsDisplayed("Test Product 1"),
            ProductScreen.productIsDisplayed("Test Product 2").map(negateStep),
            ProductScreen.productIsDisplayed("1234567890123"),
            ProductScreen.searchProduct("Red"),
            ProductScreen.productIsDisplayed("Product with Variant"),
            ProductScreen.productIsDisplayed("Test Product 1").map(negateStep),
            ProductScreen.productIsDisplayed("Test Product 2").map(negateStep),
            ProductScreen.productIsDisplayed("Apple").map(negateStep),
            ProductScreen.productIsDisplayed("1234567890123").map(negateStep),
            ProductScreen.searchProduct("variant_barcode_1"),
            ProductScreen.productIsDisplayed("Product with Variant"),
            ProductScreen.searchProduct("variant_barcode_2"),
            ProductScreen.productIsDisplayed("Product with Variant"),
            ProductScreen.searchProduct("Product with Variant"),
            ProductScreen.productIsDisplayed("Product with Variant"),
            ProductScreen.searchProduct("VARIANT_1"),
            ProductScreen.productIsDisplayed("Product with Variant"),
            ProductScreen.searchProduct("VARIANT_2"),
            ProductScreen.productIsDisplayed("Product with Variant"),
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
            Dialog.isNot(),
            ProductScreen.clickPartnerButton(),
            negateStep(PartnerList.checkCustomerShown("Z partner to scroll")),
            PartnerList.scrollBottom(),
            ProductScreen.clickCustomer("Z partner to scroll"),
        ].flat(),
});

registry.category("web_tour.tours").add("test_product_create_update_from_frontend", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickSubcategory("Chair test"),
            Chrome.clickMenuOption("Create Product"),

            // Verify that the "New Product" dialog is displayed.
            Dialog.is({ title: "New Product" }),
            {
                trigger: ".modal:not(.o_inactive_modal) .modal-footer button:contains('Add & New')",
            },
            {
                trigger:
                    ".modal:not(.o_inactive_modal) .modal-footer button:contains('Add & Close')",
            },

            // Create a new product from frontend.
            ProductScreen.createProductFromFrontend(
                "Test Frontend Product",
                "710535977349",
                "20.0"
            ),
            Dialog.confirm("Add & New", ".btn-primary"),
            // A fresh "New Product" dialog should reopen for the second product.
            Dialog.is({ title: "New Product" }),
            ProductScreen.createProductFromFrontend(
                "Test Frontend Product 2",
                "710535977350",
                "30.0"
            ),
            Dialog.confirm("Add & Close", ".btn-secondary"),
            {
                trigger: ".product-list article:contains(Test Frontend Product)",
            },
            {
                trigger: ".product-list article:contains(Test Frontend Product 2)",
            },

            ProductScreen.longPressProduct("Test Frontend Product"),
            Dialog.confirm("Edit", ".btn-secondary"),
            // Verify that the "Edit Product" dialog is displayed.
            Dialog.is({ title: "Edit Product" }),

            // Edit the product with new details.
            // First wait 1 seconds as the write_date timestamp is precise to the second,
            // if the change is done in the same second as the creation, the product will not be updated.
            {
                trigger: "body",
                run: () =>
                    new Promise((resolve) => {
                        setTimeout(resolve, 1000); // wait 1 second
                    }),
            },
            ProductScreen.editProductFromFrontend(
                "Test Frontend Product Edited",
                "710535977348",
                "50.0"
            ),
            Dialog.confirm("save"),

            ProductScreen.clickDisplayedProduct("Test Frontend Product Edited"),
            inLeftSide([
                ...ProductScreen.selectedOrderlineHasDirect(
                    "Test Frontend Product Edited",
                    "1",
                    "50.0"
                ),
            ]),
            ProductScreen.longPressProduct("Test Frontend Product Edited"),
            Dialog.confirm("Edit", ".btn-secondary"),
            Dialog.is({ title: "Edit Product" }),
            // Product 'taxes_id' field should be reaonly (cause already in the cart)
            ProductScreen.ensureTaxesInputIsReadonly(),
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
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Acme Corporation"),
            Chrome.createFloatingOrder(),
            ProductScreen.clickDisplayedProduct("Desk Pad"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            FeedbackScreen.isShown(),
            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_fiscal_position_tax_group_labels", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Test Product"),
            ProductScreen.totalAmountIs("115.00"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank", true, { remaining: "0.00" }),
            PaymentScreen.clickValidate(),
            FeedbackScreen.isShown(),
            FeedbackScreen.checkTicketData({
                cssRules: [
                    {
                        css: "tr[name='taxes_line']",
                        text: "Tax Group 15%",
                    },
                ],
            }),
            FeedbackScreen.clickNextOrder(),
            ProductScreen.clickDisplayedProduct("Test Product"),
            ProductScreen.totalAmountIs("115.00"),
            ProductScreen.clickFiscalPosition("Fiscal Position Test"),
            ProductScreen.totalAmountIs("105.00"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank", true, { remaining: "0.00" }),
            PaymentScreen.clickValidate(),
            FeedbackScreen.isShown(),
            FeedbackScreen.checkTicketData({
                cssRules: [
                    {
                        css: "tr[name='taxes_line']",
                        text: "Tax Group 5%",
                    },
                ],
            }),
        ].flat(),
});

registry.category("web_tour.tours").add("test_product_long_press", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.longPressProduct("Test Product"),
            Dialog.is(),
            {
                content: "Check On hand quantity is display on product info popup",
                trigger: ".section-inventory .on-hand:contains('0')",
            },
            {
                content: "Check that VAT label is present in the product details popup",
                trigger: ".section-financials .vat-label:contains('Tax')",
            },
            {
                content: "Check that VAT value is correct in the product details popup",
                trigger: ".section-financials .vat-value:contains('$ 15.00 (Parent Tax)')",
            },
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

registry.category("web_tour.tours").add("test_archived_product_removed_and_order_is_refunded", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("A Test Product"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            FeedbackScreen.isShown(),
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
                trigger: `[data-icon="more_vert"]`,
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
            // Refund.
            Chrome.clickOrders(),
            TicketScreen.selectFilter("Paid"),
            TicketScreen.selectOrder("0001"),
            TicketScreen.confirmRefund(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            FeedbackScreen.isShown(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_preset_timing_retail", {
    steps: () =>
        [
            Chrome.freezeDateTime(1764583200000), // 1 dec 2025 - 10:00
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            ProductScreen.selectPreset("Dine in", "Delivery", false),
            PartnerList.clickPartner("A simple PoS man!"),
            Chrome.presetTimingSlotHourNotExists("9:00am"),
            Chrome.selectPresetTimingSlotHour({ title: "delivery", hour: "3:00pm" }),
            Chrome.presetTimingSlotIs("3:00pm"),
            Chrome.createFloatingOrder(),
            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            Chrome.clickOrders(),
            TicketScreen.nthRowContains(2, "A simple PoS man!"),
            TicketScreen.nthRowContains(2, "Delivery", false),
            TicketScreen.nthRowContains(1, "002"),
            TicketScreen.nthRowContains(1, "Dine in", false),
            TicketScreen.selectOrder("002"),
            TicketScreen.loadSelectedOrder(),
            ProductScreen.selectPreset("Dine in", "Delivery", false),
            PartnerList.clickPartner("A simple PoS man!"),
            Chrome.presetTimingSlotHourNotExists("9:00am"),
            Chrome.selectPresetTimingSlotHour({ title: "delivery", hour: "5:00pm" }),
            Chrome.presetTimingSlotIs("5:00pm"),
            Chrome.isSynced(),
            Chrome.clickOrders(),
            TicketScreen.nthRowContains(2, "002"),
            TicketScreen.nthRowContains(2, "Delivery", false),
            {
                content:
                    "Simulate order cancellation from backend and check that the order is removed from the PoS",
                trigger: "body",
                run: async () => {
                    const latestOrder = posmodel.models["pos.order"].getAll()[0];
                    if (typeof latestOrder.id !== "number") {
                        // Wait for the order to be synced with the server.
                        await new Promise((resolve) => setTimeout(resolve, 1500));
                    }
                    await posmodel.data.call(
                        "pos.order",
                        "action_pos_order_cancel",
                        [latestOrder.id],
                        {
                            context: {
                                active_ids: [latestOrder.id],
                            },
                        }
                    );
                },
            },
            negateStep(...TicketScreen.nthRowContains(2, "002")),
        ].flat(),
});

registry
    .category("web_tour.tours")
    .add("test_fast_payment_validation_from_product_screen_without_automatic_receipt_printing", {
        steps: () =>
            [
                Chrome.startPoS(),
                Dialog.confirm("Open Register"),
                PartnerList.searchCustomerValue("APartner Full", true),
                PartnerList.clickPartner("APartner Full"),
                ProductScreen.clickDisplayedProduct("Desk Organizer"),
                ProductScreen.clickFastPaymentButton("Bank"),
                FeedbackScreen.isShown(),
                PartnerList.isShown().map(negateStep),
                FeedbackScreen.clickNextOrder(),
                PartnerList.searchCustomerValue("APartner Full", true),
                PartnerList.clickPartner("APartner Full"),
                ProductScreen.clickDisplayedProduct("Desk Organizer"),
                ProductScreen.clickPayButton(),
                PaymentScreen.clickPaymentMethod("Bank"),
                PaymentScreen.clickValidate(),
                FeedbackScreen.isShown(),
                PartnerList.isShown().map(negateStep),
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
                FeedbackScreen.clickNextOrder(),
                ProductScreen.isShown(),
                ProductScreen.clickDisplayedProduct("Desk Organizer"),
                ProductScreen.clickPayButton(),
                PaymentScreen.clickPaymentMethod("Bank"),
                PaymentScreen.clickValidate(),
                FeedbackScreen.isShown(),
                ProductScreen.isShown(),
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

registry.category("web_tour.tours").add("test_load_pos_demo_data_with_member_role", {
    steps: () =>
        [
            Chrome.startPoS(),
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
            ProductScreen.totalAmountIs("7,771.00"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            FeedbackScreen.isShown(),
            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_weight_product", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Acme Corporation"),
            ProductScreen.clickDisplayedProduct("Vanela Gathiya"),
            inLeftSide([
                Numpad.click("Price"),
                Numpad.click("4"),
                Numpad.click("0"),
                ...Order.hasLine({
                    productName: "Vanela Gathiya",
                    quantity: "4",
                    price: "40",
                    withClass: ".selected",
                }),
            ]),
            ProductScreen.clickDisplayedProduct("Configurable Chair"),
            ProductConfiguratorPopup.pickRadio("Other"),
            ProductConfiguratorPopup.fillCustomAttribute("Test custom value"),
            Chrome.clickBtn("Add"),
            inLeftSide([
                Numpad.click("Price"),
                Numpad.click("4"),
                Numpad.click("0"),
                ...Order.hasLine({
                    productName: "Configurable Chair",
                    quantity: "1",
                    price: "40",
                    withClass: ".selected",
                }),
            ]),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickInvoiceButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            FeedbackScreen.isShown(),
            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_customer_search_prefilled_on_create", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickPartnerButton(),
            PartnerList.searchCustomer("test customer"),
            {
                content: "Wait",
                trigger: "body",
                async run() {
                    await delay(100); //Search input debounce 100
                },
            },
            PartnerList.clickPartnerCreateBtn(),

            PartnerList.checkInputForm("name", "test customer"),
            PartnerList.selectFormDiscard(),

            PartnerList.searchCustomer("+(123) 45.67-89"),
            {
                content: "Wait",
                trigger: "body",
                async run() {
                    await delay(100); //Search input debounce 100
                },
            },
            PartnerList.clickPartnerCreateBtn(),
            PartnerList.checkInputForm("phone", "+(123) 45.67-89"),
            PartnerList.selectFormDiscard(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_default_fiscal_position_allowed", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Partner Test 1", true),
            ProductScreen.checkFiscalPosition("Allowed"),
            ProductScreen.clickControlButtonMore(),
            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_barcode_scan_preselect_always_variant", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            scan_barcode("VAR_RED_001"),

            ProductConfiguratorPopup.pickRadio("Large"),
            Dialog.confirm("Add"),
            ProductScreen.selectedOrderlineHas(
                "Variant Barcode Product",
                "1.0",
                "10.0",
                "Red, Large"
            ),

            scan_barcode("VAR_BLUE_001"),
            Dialog.confirm("Add"),
            ProductScreen.selectedOrderlineHas(
                "Variant Barcode Product",
                "1.0",
                "10.0",
                "Blue, Small"
            ),

            Chrome.endTour(),
        ].flat(),
});
