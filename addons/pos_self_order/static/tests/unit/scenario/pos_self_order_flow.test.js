import { expect, test } from "@odoo/hoot";
import { mockDate } from "@odoo/hoot-mock";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { setupSelfPosEnv } from "@pos_self_order/../tests/unit/utils";
import { definePosSelfModels } from "@pos_self_order/../tests/unit/data/generate_model_definitions";
import { SelfOrderRouter } from "@pos_self_order/app/services/self_order_router_service";
import * as Utils from "@pos_self_order/../tests/unit/ui_utils";

definePosSelfModels();

test("self_order_is_close: closed POS hides checkout", async () => {
    await setupSelfPosEnv(
        "kiosk",
        "table",
        "each",
        {
            use_presets: false,
            available_preset_ids: [],
        },
        false
    );
    await Utils.checkIsClosed();
    await Utils.clickOrderNow();
    await Utils.clickCategory("Miscellaneous");
    await Utils.clickProduct("Coca-Cola");
    await Utils.checkIsNoBtn("Checkout");
});

test("self_order_is_open_consultation: consultation mode opens then hides Order", async () => {
    await setupSelfPosEnv("consultation", "counter", "each", {}, true);
    await Utils.clickOrderNow();
    await Utils.selectLocation("Test-Takeout");
    await Utils.checkIsOpened();
    await Utils.clickCategory("Miscellaneous");
    await Utils.clickProduct("Coca-Cola");
    await Utils.checkIsNoBtn("Order");
});

test("self_order_landing_page_carousel: no My Order button and carousel auto-plays", async () => {
    await setupSelfPosEnv("kiosk", "counter", "each", {}, true);
    await Utils.checkIsNoBtn("My Order");
    await Utils.checkCarouselAutoPlaying();
});

test("self_order_landing_page_carousel_mobile: mobile landing page carousel auto-plays", async () => {
    await setupSelfPosEnv("mobile", "counter", "each", {}, true);
    await Utils.checkIsNoBtn("My Order");
    await Utils.checkCarouselAutoPlaying();
});

test("self_order_landing_page_carousel_consultation: consultation landing page carousel auto-plays", async () => {
    await setupSelfPosEnv("consultation", "counter", "each", {}, true);
    await Utils.checkIsNoBtn("My Order");
    await Utils.checkCarouselAutoPlaying();
});

test("self_order_pos_closed: closed POS blocks checkout for normal/attribute/combo", async () => {
    await setupSelfPosEnv("kiosk", "counter", "each", {}, false);
    await Utils.checkIsClosed();
    await Utils.clickOrderNow();
    await Utils.selectLocation("Test-Takeout");
    await Utils.clickCategory("Miscellaneous");
    await Utils.clickProduct("Coca-Cola");
    await Utils.checkIsNoBtn("Checkout");
    await Utils.clickProduct("Desk Organizer");
    await Utils.setupAttribute([
        { name: "Size", value: "M" },
        { name: "Fabric", value: "Leather" },
    ]);
    await Utils.checkIsNoBtn("Add to cart");
    await Utils.clickDiscard();
    await Utils.clickCategory("Combos");
    await Utils.clickProduct("Office Combo");
    await Utils.setupCombo([
        {
            product: "Desk Organizer",
            attributes: [
                { name: "Size", value: "M" },
                { name: "Fabric", value: "Leather" },
            ],
        },
    ]);
    await Utils.clickBtn("Next");
    await Utils.setupCombo([
        {
            product: "Combo Product 5",
            attributes: [],
        },
    ]);
    await Utils.clickBtn("Next");
    await Utils.setupCombo([
        {
            product: "Combo Product 8",
            attributes: [],
        },
    ]);
    await Utils.clickBtn("Next");
    await Utils.checkIsNoBtn("Add to cart");
});

test("self_order_pos_closed_mobile: mobile closed POS blocks checkout", async () => {
    await setupSelfPosEnv("mobile", "counter", "each", {}, false);
    await Utils.checkIsClosed();
    await Utils.clickOrderNow();
    await Utils.selectLocation("Test-Takeout");
    await Utils.clickCategory("Miscellaneous");
    await Utils.clickProduct("Coca-Cola");
    await Utils.checkIsNoBtn("Checkout");
    await Utils.clickProduct("Desk Organizer");
    await Utils.setupAttribute([
        { name: "Size", value: "M" },
        { name: "Fabric", value: "Leather" },
    ]);
    await Utils.checkIsNoBtn("Add to cart");
    await Utils.clickDiscard();
    await Utils.clickCategory("Combos");
    await Utils.clickProduct("Office Combo");
    await Utils.setupCombo([
        {
            product: "Desk Organizer",
            attributes: [
                { name: "Size", value: "M" },
                { name: "Fabric", value: "Leather" },
            ],
        },
    ]);
    await Utils.clickBtn("Next");
    await Utils.setupCombo([
        {
            product: "Combo Product 5",
            attributes: [],
        },
    ]);
    await Utils.clickBtn("Next");
    await Utils.setupCombo([
        {
            product: "Combo Product 8",
            attributes: [],
        },
    ]);
    await Utils.clickBtn("Next");
    await Utils.checkIsNoBtn("Add to cart");
});

test("self_order_pos_closed_consultation: consultation closed POS blocks checkout", async () => {
    await setupSelfPosEnv("consultation", "counter", "each", {}, false);
    await Utils.checkIsClosed();
    await Utils.clickOrderNow();
    await Utils.selectLocation("Test-Takeout");
    await Utils.clickCategory("Miscellaneous");
    await Utils.clickProduct("Coca-Cola");
    await Utils.checkIsNoBtn("Checkout");
    await Utils.clickProduct("Desk Organizer");
    await Utils.setupAttribute([
        { name: "Size", value: "M" },
        { name: "Fabric", value: "Leather" },
    ]);
    await Utils.checkIsNoBtn("Add to cart");
    await Utils.clickDiscard();
    await Utils.clickCategory("Combos");
    await Utils.clickProduct("Office Combo");
    await Utils.setupCombo([
        {
            product: "Desk Organizer",
            attributes: [
                { name: "Size", value: "M" },
                { name: "Fabric", value: "Leather" },
            ],
        },
    ]);
    await Utils.clickBtn("Next");
    await Utils.setupCombo([
        {
            product: "Combo Product 5",
            attributes: [],
        },
    ]);
    await Utils.clickBtn("Next");
    await Utils.setupCombo([
        {
            product: "Combo Product 8",
            attributes: [],
        },
    ]);
    await Utils.clickBtn("Next");
    await Utils.checkIsNoBtn("Add to cart");
});

test("kiosk_order_pos_closed: kiosk closed blocks checkout across categories", async () => {
    await setupSelfPosEnv("kiosk", "counter", "each", {}, false);
    await Utils.checkIsClosed();
    await Utils.clickOrderNow();
    await Utils.selectLocation("Test-In");
    await Utils.clickCategory("Miscellaneous");
    await Utils.clickProduct("Coca-Cola");
    await Utils.checkIsNoBtn("Checkout");
    await Utils.clickProduct("Desk Organizer");
    await Utils.setupAttribute([
        { name: "Size", value: "M" },
        { name: "Fabric", value: "Leather" },
    ]);
    await Utils.checkIsNoBtn("Add to cart");
    await Utils.clickDiscard();
    await Utils.clickCategory("Combos");
    await Utils.clickProduct("Office Combo");
    await Utils.setupCombo([
        {
            product: "Desk Organizer",
            attributes: [
                { name: "Size", value: "M" },
                { name: "Fabric", value: "Leather" },
            ],
        },
    ]);
    await Utils.clickBtn("Next");
    await Utils.setupCombo([
        {
            product: "Combo Product 5",
            attributes: [],
        },
    ]);
    await Utils.clickBtn("Next");
    await Utils.setupCombo([
        {
            product: "Combo Product 8",
            attributes: [],
        },
    ]);
    await Utils.clickBtn("Next");
    await Utils.checkIsNoBtn("Add to cart");
});

test("test_preparation_categories_are_loaded: only preparation categories visible", async () => {
    const store = await setupSelfPosEnv(
        "kiosk",
        "counter",
        "each",
        {
            limit_categories: true,
            iface_available_categ_ids: [208],
            use_presets: false,
            available_preset_ids: [],
        },
        true
    );
    await Utils.clickOrderNow();
    const availableCategIds = store.availableCategories.map((categ) => categ.name);
    if (!availableCategIds.includes("MOOL") || availableCategIds.length !== 1) {
        throw new Error("Preparation categories are not correctly loaded");
    }
    await Utils.checkCategoryBtn("MOOL");
    for (const category of [
        "Miscellaneous",
        "Combos",
        "Test Category",
        "Specials",
        "Category 1",
        "Category 2",
    ]) {
        Utils.checkIsNoCategoryBtn(category);
    }
});

test("self_attribute_selector: M+Leather then L+Leather, order, verify cart", async () => {
    await setupSelfPosEnv(
        "mobile",
        "counter",
        "each",
        { use_presets: false, available_preset_ids: [] },
        true
    );
    await Utils.clickOrderNow();
    await Utils.clickCategory("Miscellaneous");
    await Utils.clickProduct("Desk Organizer");
    await Utils.setupAttribute([
        { name: "Size", value: "M" },
        { name: "Fabric", value: "Leather" },
        { name: "Colour", value: "White" },
    ]);
    await Utils.clickBtn("Add to cart");
    await Utils.clickBtn("Checkout");
    await Utils.checkAttributeInCart("Desk Organizer", [
        { name: "Size", value: "M" },
        { name: "Fabric", value: "Leather" },
        { name: "Colour", value: "White" },
    ]);
    await Utils.checkProductInCart("Desk Organizer", "7.02", "1");
    await Utils.clickBackFromCart();
    await Utils.clickProduct("Desk Organizer");
    await Utils.setupAttribute([
        { name: "Size", value: "L" },
        { name: "Fabric", value: "Leather" },
        { name: "Colour", value: "Blue" },
    ]);
    await Utils.clickBtn("Add to cart");
    await Utils.clickBtn("Checkout");
    await Utils.checkAttributeInCart("Desk Organizer", [
        { name: "Size", value: "L" },
        { name: "Fabric", value: "Leather" },
        { name: "Colour", value: "Blue" },
    ]);
    await Utils.checkProductInCart("Desk Organizer", "7.02", "1");
    await Utils.clickBtn("Order");
    await Utils.clickBtn("Ok");
    await Utils.clickBtn("My Order");
    await Utils.checkIsNoBtn("Order");
    await Utils.clickBackFromCart();
    await Utils.checkIsNoBtn("Order Now");
});

test("selfAlwaysAttributeVariants: Chair White then Red variants", async () => {
    await setupSelfPosEnv(
        "mobile",
        "counter",
        "each",
        { use_presets: false, available_preset_ids: [] },
        true
    );
    await Utils.clickOrderNow();
    await Utils.waitProduct("Chair");
    await Utils.clickProduct("Chair");
    await Utils.setupAttribute([{ name: "Color", value: "White" }]);
    await Utils.clickBtn("Add to cart");
    await Utils.clickBtn("Checkout");
    await Utils.checkProductInCart("Chair", "10", "1");
    await Utils.checkAttributeInCart("Chair", [{ name: "Color", value: "White" }]);
    await Utils.clickBackFromCart();
    await Utils.clickProduct("Chair");
    await Utils.setupAttribute([{ name: "Color", value: "Red" }]);
    await Utils.clickBtn("Add to cart");
    await Utils.clickBtn("Checkout");
    await Utils.checkProductInCart("Chair", "15", "1");
    await Utils.checkAttributeInCart("Chair", [{ name: "Color", value: "Red" }]);
    await Utils.clickBtn("Order");
    await Utils.clickBtn("Ok");
    await Utils.clickBtn("My Order");
    await Utils.checkIsNoBtn("Order");
    await Utils.clickBackFromCart();
    await Utils.checkIsNoBtn("Order Now");
});

test("self_order_product_info: info popup shows product description", async () => {
    await setupSelfPosEnv("mobile", "counter", "each", {}, true);
    await Utils.clickOrderNow();
    await Utils.selectLocation("In");
    await Utils.clickProductInfo("Product Info Test");
    await Utils.dialogBodyIs("Nice Product");
});

test("self_attribute_selector_shows_images: color dot and image displayed", async () => {
    await setupSelfPosEnv(
        "mobile",
        "counter",
        "each",
        { use_presets: false, available_preset_ids: [] },
        true
    );
    await Utils.clickOrderNow();
    await Utils.clickProduct("Desk Organizer");
    await Utils.attributeHasColorDot("White");
    await Utils.attributeHasImage("Blue");
});

test("self_combo_selector: Office Combo with attributes + 2 plain items", async () => {
    await setupSelfPosEnv(
        "mobile",
        "counter",
        "each",
        { use_presets: false, available_preset_ids: [] },
        true
    );
    await Utils.clickOrderNow();
    await Utils.clickCategory("Test Category");
    await Utils.clickProduct("Office Combo");
    await Utils.setupCombo([
        {
            product: "Desk Organizer",
            attributes: [
                { name: "Size", value: "M" },
                { name: "Fabric", value: "Leather" },
            ],
        },
    ]);
    await Utils.clickBtn("Next");
    await Utils.setupCombo([
        {
            product: "Combo Product 5",
            attributes: [],
        },
    ]);
    await Utils.clickBtn("Next");
    await Utils.setupCombo([
        {
            product: "Combo Product 8",
            attributes: [],
        },
    ]);
    await Utils.clickBtn("Next");
    await Utils.clickBtn("Add to cart");
    await Utils.clickBtn("Checkout");
    await Utils.increaseCartItemQty();
    await Utils.checkComboInCart("Office Combo", [
        {
            product: "Desk Organizer",
            attributes: [
                { name: "Size", value: "M" },
                { name: "Fabric", value: "Leather" },
            ],
        },
        {
            product: "Combo Product 5",
            attributes: [],
        },
        {
            product: "Combo Product 8",
            attributes: [],
        },
    ]);
    await Utils.clickBtn("Order");
    await Utils.checkOrderNumberShown();
    await Utils.checkOrderNumberIs("S", "1");
    await Utils.clickBtn("Ok");
    await Utils.checkIsNoBtn("Order Now");
});

test("self_combo_selector_category: Test Combo selection", async () => {
    await setupSelfPosEnv(
        "mobile",
        "counter",
        "each",
        { use_presets: false, available_preset_ids: [] },
        true
    );
    await Utils.clickOrderNow();
    await Utils.clickCategory("Test Category");
    await Utils.clickProduct("Test Combo");
    await Utils.setupCombo([
        {
            product: "Combo Product 5",
            attributes: [],
        },
    ]);
    await Utils.clickBtn("Next");
    await Utils.clickBtn("Add to cart");
    await Utils.clickBtn("Checkout");
    await Utils.clickBtn("Order");
    await Utils.clickBtn("Ok");
    await Utils.checkIsNoBtn("Order Now");
});

test("test_product_dont_display_all_variants: Meal Combo with always/never variants", async () => {
    await setupSelfPosEnv("kiosk", "table", "each", {}, true);
    await Utils.clickOrderNow();
    await Utils.selectLocation("Test-In");
    await Utils.clickCategory("Uncategorised");
    await Utils.clickProduct("Meal Combo");
    await Utils.clickComboProduct("Coke always never");
    await Utils.clickBtn("Red");
    await Utils.clickBtn("Next");
    await Utils.clickBtn("Add to cart");
    await Utils.clickProduct("Meal Combo");
    await Utils.clickComboProduct("Coke always only");
    await Utils.clickBtn("Add to cart");
    await Utils.clickProduct("Meal Combo");
    await Utils.clickComboProduct("Coke never only");
    await Utils.clickBtn("Red");
    await Utils.clickBtn("Add to cart");
});

test("test_self_order_combo_multiple_qty: Combo Drinks qty + Price for drinks qty", async () => {
    await setupSelfPosEnv("kiosk", "table", "each", {}, true);
    await Utils.clickOrderNow();
    await Utils.selectLocation("Test-In");
    await Utils.clickCategory("Uncategorised");
    await Utils.clickProduct("Combo Drinks");
    await Utils.setupCombo([
        {
            product: "Water",
            attributes: [],
        },
    ]);
    await Utils.clickBtn("Next");
    await Utils.clickBtn("Add to cart");
    await Utils.clickBtn("Checkout");
    await Utils.increaseCartItemQty();
    await Utils.clickBtn("Order");
    await Utils.clickNumpad("2");
    await Utils.clickBtn("Order");
    await Utils.clickBtn("Close");
    await Utils.clickBtn("Order Now");
    await Utils.selectLocation("Test-In");
    await Utils.clickCategory("Uncategorised");
    await Utils.clickProduct("Price for drinks");
    await Utils.setupCombo([
        {
            product: "Water 2",
            attributes: [],
        },
    ]);
    await Utils.clickBtn("Next");
    await Utils.clickBtn("Add to cart");
    await Utils.clickBtn("Checkout");
    await Utils.increaseCartItemQty();
    await Utils.increaseCartItemQty();
    await Utils.clickBtn("Order");
    await Utils.clickNumpad("3");
    await Utils.clickBtn("Order");
});

test("test_self_combo_extra_price_selection_and_confirmation: price badge + Extra badge verification", async () => {
    await setupSelfPosEnv(
        "mobile",
        "counter",
        "each",
        { use_presets: false, available_preset_ids: [] },
        true
    );
    await Utils.clickOrderNow();
    await Utils.clickCategory("Combos");
    await Utils.clickProduct("Office Combo");
    await Utils.verifyItemHasNoExtraBadge("Combo Product 1");
    await Utils.clickComboProduct("Combo Product 1");
    await Utils.verifyItemHasNoExtraBadge("Combo Product 1");
    await Utils.clickComboProduct("Combo Product 1");
    await Utils.verifyItemHasExtraBadge("Combo Product 1", 10);
    await Utils.clickComboProduct("Combo Product 3");
    await Utils.verifyItemHasExtraBadge("Combo Product 3", 12);
    await Utils.clickBtn("Next");
    await Utils.verifyItemHasPriceBadge("Combo Product 4", 20);
    await Utils.verifyItemHasPriceBadge("Combo Product 5", 22);
    await Utils.clickComboProduct("Combo Product 4");
    await Utils.clickBtn("Next");
    await Utils.clickComboProduct("Combo Product 6");
    await Utils.clickBtn("Next");
    await Utils.verifyConfirmationPageShown();
    await Utils.verifyConfirmationHasExtraPrice("Combo Product 1");
    await Utils.verifyConfirmationHasExtraPrice("Combo Product 3");
    await Utils.verifyConfirmationHasExtraPrice("Combo Product 4");
    await Utils.clickBtn("Add to cart");
});

test("self_kiosk_each_table_takeaway_in: table mode, order, qty numpad, close, verify", async () => {
    await setupSelfPosEnv(
        "kiosk",
        "table",
        "each",
        { use_presets: false, available_preset_ids: [] },
        true
    );
    await Utils.checkIsNoBtn("My Order");
    await Utils.clickOrderNow();
    await Utils.clickCategory("Miscellaneous");
    await Utils.checkReferenceNotInProductName("Coca-Cola", "12345");
    await Utils.clickProduct("Coca-Cola");
    await Utils.clickBtn("Checkout");
    await Utils.checkProductInCart("Coca-Cola", "2.53", "1");
    await Utils.clickBtn("Order");
    await Utils.clickNumpad("3");
    await Utils.clickBtn("Order");
    await Utils.checkOrderNumberShown();
    await Utils.checkOrderNumberIs("K1-", "1");
    await Utils.clickBtn("Close");
    await Utils.checkIsNoBtn("My Order");
    await Utils.clickBtn("Order Now");
    await Utils.clickCategory("Miscellaneous");
    await Utils.checkIsDisabledBtn("Checkout");
});

test("self_kiosk_each_table_takeaway_out: table mode, order, close, URL validation", async () => {
    const store = await setupSelfPosEnv(
        "kiosk",
        "counter",
        "each",
        { use_presets: false, available_preset_ids: [] },
        true
    );
    await Utils.checkIsNoBtn("My Order");
    await Utils.clickOrderNow();
    await Utils.clickCategory("Miscellaneous");
    await Utils.clickProduct("Coca-Cola");
    await Utils.clickBtn("Checkout");
    await Utils.checkProductInCart("Coca-Cola", "2.53", "1");
    await Utils.clickBtn("Order");
    await Utils.clickBtn("Close");
    await Utils.checkIsNoBtn("My Order");
    await Utils.clickBtn("Order Now");
    await Utils.clickCategory("Miscellaneous");
    await Utils.checkIsDisabledBtn("Checkout");
    const selfInvoicingURL = `${store.currentOrder.config._base_url}/pos/ticket`;
    expect(selfInvoicingURL).not.toInclude("undefined");
    expect(new URL(selfInvoicingURL)).toBeInstanceOf(URL);
});

test("self_kiosk_each_counter_takeaway_in: counter mode multi-category, total check", async () => {
    await setupSelfPosEnv("kiosk", "counter", "each", {}, true);
    await Utils.checkIsNoBtn("My Order");
    await Utils.clickOrderNow();
    await Utils.selectLocation("Test-In");
    await Utils.clickCategory("Miscellaneous");
    await Utils.clickProduct("Coca-Cola");
    await Utils.clickCategory("Uncategorised");
    await Utils.clickProduct("Yummy Burger");
    await Utils.clickProduct("Taxi Burger");
    await Utils.clickBtn("Checkout");
    await Utils.checkProductInCart("Coca-Cola", "2.53");
    await Utils.checkProductInCart("Yummy Burger", "10");
    await Utils.checkProductInCart("Taxi Burger", "11");
    await Utils.checkTotalPrice("23.53");
    await Utils.clickBtn("Order");
    await Utils.clickNumpad("3");
    await Utils.clickBtn("Order");
    await Utils.clickBtn("Close");
    await Utils.checkIsNoBtn("My Order");
    await Utils.clickBtn("Order Now");
    await Utils.selectLocation("Test-In");
    await Utils.clickCategory("Miscellaneous");
    await Utils.checkIsDisabledBtn("Checkout");
});

test("self_kiosk_each_counter_takeaway_out: counter mode with name/phone fill", async () => {
    await setupSelfPosEnv("kiosk", "counter", "each", {}, true);
    await Utils.checkIsNoBtn("My Order");
    await Utils.clickOrderNow();
    await Utils.selectLocation("Test-Takeout");
    await Utils.clickCategory("Miscellaneous");
    await Utils.clickProduct("Coca-Cola");
    await Utils.clickBtn("Checkout");
    await Utils.checkProductInCart("Coca-Cola", "2.53");
    await Utils.clickBtn("Order");
    await Utils.fillInput("Name", "Mr Kiosk");
    await Utils.fillInput("Phone", "490904390");
    await Utils.clickBtn("Continue");
    await Utils.clickBtn("Close");
    await Utils.checkIsNoBtn("My Order");
    await Utils.clickBtn("Order Now");
    await Utils.selectLocation("Test-Takeout");
    await Utils.clickCategory("Miscellaneous");
    await Utils.checkIsDisabledBtn("Checkout");
});

test("self_order_kiosk_cancel: cancel order from product list", async () => {
    await setupSelfPosEnv(
        "kiosk",
        "counter",
        "each",
        { use_presets: false, available_preset_ids: [] },
        true
    );
    await Utils.checkIsNoBtn("My Order");
    await Utils.clickOrderNow();
    await Utils.clickCategory("Miscellaneous");
    await Utils.clickProduct("Coca-Cola");
    await Utils.clickProduct("Fanta");
    await Utils.clickBtn("Checkout");
    await Utils.checkProductInCart("Coca-Cola", "2.53", "1");
    await Utils.checkProductInCart("Fanta", "2.53", "1");
    await Utils.clickBackFromCart();
    await Utils.clickCancelFromProductList();
    await Utils.clickBtn("Order Now");
    await Utils.clickCategory("Miscellaneous");
    await Utils.checkIsDisabledBtn("Checkout");
});

test("test_duplicate_order_kiosk: order then close, no My Order button", async () => {
    await setupSelfPosEnv(
        "kiosk",
        "counter",
        "each",
        { use_presets: false, available_preset_ids: [] },
        true
    );
    await Utils.checkIsNoBtn("My Order");
    await Utils.clickOrderNow();
    await Utils.clickCategory("Miscellaneous");
    await Utils.clickProduct("Coca-Cola");
    await Utils.clickBtn("Checkout");
    await Utils.checkProductInCart("Coca-Cola", "2.53");
    await Utils.clickBtn("Order");
    await Utils.clickBtn("Close");
    await Utils.checkIsNoBtn("My Order");
});

test("kiosk_order_price_null: zero-price product order", async () => {
    await setupSelfPosEnv(
        "kiosk",
        "counter",
        "each",
        { use_presets: false, available_preset_ids: [] },
        true
    );
    await Utils.checkIsNoBtn("My Order");
    await Utils.clickOrderNow();
    await Utils.clickCategory("Miscellaneous");
    await Utils.clickProduct("Ketchup");
    await Utils.clickBtn("Checkout");
    await Utils.checkProductInCart("Ketchup", "0.00");
    await Utils.clickBtn("Order");
    await Utils.checkOrderNumberShown();
    await Utils.checkBtn("Close");
});

test("test_self_order_kiosk_combo_sides: combo with attribute selection then Next", async () => {
    await setupSelfPosEnv("kiosk", "table", "each", {}, true);
    await Utils.clickOrderNow();
    await Utils.selectLocation("Test-In");
    await Utils.clickCategory("Combos");
    await Utils.clickProduct("Office Combo");
    await Utils.setupCombo([
        {
            product: "Desk Organizer",
            attributes: [
                { name: "Size", value: "M" },
                { name: "Fabric", value: "Leather" },
            ],
        },
    ]);
    await Utils.clickBtn("Next");
});

test("test_self_order_kiosk_combo_qty_max_free: combo with max free qty increase", async () => {
    await setupSelfPosEnv("kiosk", "table", "each", {}, true);
    await Utils.clickOrderNow();
    await Utils.selectLocation("Test-In");
    await Utils.clickCategory("Combos");
    await Utils.clickProduct("Kiosk Qty Combo");
    await Utils.clickComboProduct("Combo Product 4");
    await Utils.increaseComboItemQty("Combo Product 4", 3);
    await Utils.clickBtn("Next");
    await Utils.clickBtn("Add to cart");
});

test("test_self_order_kiosk_unpaid: unpaid kiosk order", async () => {
    await setupSelfPosEnv(
        "kiosk",
        "counter",
        "each",
        { use_presets: false, available_preset_ids: [] },
        true
    );
    await Utils.clickOrderNow();
    await Utils.clickCategory("Miscellaneous");
    await Utils.clickProduct("Coca-Cola");
    await Utils.clickBtn("Checkout");
    await Utils.clickBtn("Order");
    await Utils.checkOrderNumberShown();
});

test("test_self_order_parent_category: child categories from parent", async () => {
    await setupSelfPosEnv(
        "kiosk",
        "counter",
        "each",
        {
            limit_categories: true,
            iface_available_categ_ids: [203, 204, 205],
            use_presets: false,
            available_preset_ids: [],
        },
        true
    );
    await Utils.clickOrderNow();
    await Utils.clickChildCategory("Test Child Category 1");
    await Utils.clickProduct("Coca-Cola");
    await Utils.clickChildCategory("Test Child Category 2");
    await Utils.clickProduct("Pepsi");
    await Utils.clickBtn("Checkout");
    await Utils.clickBtn("Order");
    await Utils.clickBtn("Close");
});

test("self_mobile_each_table_takeaway_in: mobile table mode, order, cancel", async () => {
    await setupSelfPosEnv("mobile", "table", "each", {}, true);
    await Utils.checkIsNoBtn("My Order");
    await Utils.clickOrderNow();
    await Utils.selectLocation("In");
    await Utils.clickProduct("Coca-Cola");
    await Utils.clickBtn("Checkout");
    await Utils.checkProductInCart("Coca-Cola", "2.53", "1");
    await Utils.clickBtn("Order");
    await Utils.clickBtn("Ok");
    await Utils.checkIsNoBtn("Order Now");
    await Utils.clickBtn("My Order");
    await Utils.checkIsNoBtn("Order");
    await Utils.clickBackFromCart();
    await Utils.checkIsNoBtn("Order Now");
    await Utils.clickBtn("My Order");
    await Utils.clickCancelOrder();
    await Utils.checkBtn("Order Now");
    await Utils.checkBtn("My Orders");
});

test("self_mobile_each_table_takeaway_out: mobile table with name/phone", async () => {
    await setupSelfPosEnv("mobile", "table", "each", {}, true);
    await Utils.checkIsNoBtn("My Order");
    await Utils.clickOrderNow();
    await Utils.selectLocation("Test-Takeout");
    await Utils.clickProduct("Coca-Cola");
    await Utils.clickBtn("Checkout");
    await Utils.checkProductInCart("Coca-Cola", "2.53", "1");
    await Utils.clickBtn("Order");
    await Utils.fillInput("Name", "Dr Dre");
    await Utils.fillInput("Phone", "490904390");
    await Utils.clickBtn("Continue");
    await Utils.clickBtn("Ok");
    await Utils.checkIsNoBtn("Order Now");
    await Utils.clickBtn("My Order");
    await Utils.checkIsNoBtn("Order");
    await Utils.clickBackFromCart();
    await Utils.checkIsNoBtn("Order Now");
});

test("self_mobile_each_counter_takeaway_in: mobile counter mode", async () => {
    await setupSelfPosEnv("mobile", "counter", "each", {}, true);
    await Utils.checkIsNoBtn("My Order");
    await Utils.clickOrderNow();
    await Utils.selectLocation("In");
    await Utils.clickProduct("Coca-Cola");
    await Utils.clickBtn("Checkout");
    await Utils.checkProductInCart("Coca-Cola", "2.53", "1");
    await Utils.clickBtn("Order");
    await Utils.clickBtn("Ok");
    await Utils.checkIsNoBtn("Order Now");
    await Utils.clickBtn("My Order");
    await Utils.checkIsNoBtn("Order");
    await Utils.clickBackFromCart();
    await Utils.checkIsNoBtn("Order Now");
});

test("self_mobile_each_counter_takeaway_out: mobile counter with name/phone", async () => {
    await setupSelfPosEnv("mobile", "counter", "each", {}, true);
    await Utils.checkIsNoBtn("My Order");
    await Utils.clickOrderNow();
    await Utils.selectLocation("Test-Takeout");
    await Utils.clickProduct("Coca-Cola");
    await Utils.clickBtn("Checkout");
    await Utils.checkProductInCart("Coca-Cola", "2.53", "1");
    await Utils.clickBtn("Order");
    await Utils.fillInput("Name", "Dr Dre");
    await Utils.fillInput("Phone", "490904390");
    await Utils.clickBtn("Continue");
    await Utils.clickBtn("Ok");
    await Utils.checkIsNoBtn("Order Now");
    await Utils.clickBtn("My Order");
    await Utils.checkIsNoBtn("Order");
    await Utils.clickBackFromCart();
    await Utils.checkIsNoBtn("Order Now");
});

test("self_mobile_meal_table_takeaway_in: meal mode, multiple orders, total/qty checks", async () => {
    await setupSelfPosEnv("mobile", "table", "meal", {}, true);
    await Utils.checkIsNoBtn("My Order");
    await Utils.clickOrderNow();
    await Utils.selectLocation("In");
    await Utils.clickProduct("Coca-Cola");
    await Utils.checkOrderTotal("2.53");
    await Utils.checkProductQty("Coca-Cola", "1");
    await Utils.clickBtn("Checkout");
    await Utils.checkProductInCart("Coca-Cola", "2.53", "1");
    await Utils.clickBtn("Order");
    await Utils.clickBtn("Ok");
    await Utils.clickBtn("Order Now");
    await Utils.clickProduct("Fanta");
    await Utils.checkOrderTotal("2.53");
    await Utils.checkProductQty("Fanta", "1");
    await Utils.clickBtn("Checkout");
    await Utils.checkProductInCart("Fanta", "2.53", "1");
    await Utils.clickBtn("Order");
    await Utils.checkConfirmationPage();
    await Utils.clickBtn("Ok");
    await Utils.clickBtn("My Order");
    await Utils.checkIsNoBtn("Order");
    await Utils.clickBackFromCart();
    await Utils.checkBtn("Order Now");
});

test("self_mobile_meal_table_takeaway_out: meal mode with name/phone", async () => {
    await setupSelfPosEnv("mobile", "table", "meal", {}, true);
    await Utils.checkIsNoBtn("My Order");
    await Utils.clickOrderNow();
    await Utils.selectLocation("Test-Takeout");
    await Utils.clickProduct("Coca-Cola");
    await Utils.checkOrderTotal("2.53");
    await Utils.checkProductQty("Coca-Cola", "1");
    await Utils.clickBtn("Checkout");
    await Utils.checkProductInCart("Coca-Cola", "2.53", "1");
    await Utils.clickBtn("Order");
    await Utils.fillInput("Name", "Dr Dre");
    await Utils.fillInput("Phone", "490904390");
    await Utils.clickBtn("Continue");
    await Utils.checkConfirmationPage();
    await Utils.clickBtn("Ok");
    await Utils.clickBtn("Order Now");
    await Utils.clickProduct("Fanta");
    await Utils.checkOrderTotal("2.53");
    await Utils.checkProductQty("Fanta", "1");
    await Utils.clickBtn("Checkout");
    await Utils.checkProductInCart("Fanta", "2.53", "1");
    await Utils.clickBtn("Order");
    await Utils.checkConfirmationPage();
    await Utils.clickBtn("Ok");
    await Utils.clickBtn("My Order");
    await Utils.checkIsNoBtn("Order");
    await Utils.clickBackFromCart();
    await Utils.checkBtn("Order Now");
});

test("self_mobile_meal_counter_takeaway_in: meal counter, confirm shown each time", async () => {
    await setupSelfPosEnv("mobile", "counter", "meal", {}, true);
    await Utils.checkIsNoBtn("My Order");
    await Utils.clickOrderNow();
    await Utils.selectLocation("In");
    await Utils.clickProduct("Coca-Cola");
    await Utils.checkOrderTotal("2.53");
    await Utils.checkProductQty("Coca-Cola", "1");
    await Utils.clickBtn("Checkout");
    await Utils.checkProductInCart("Coca-Cola", "2.53", "1");
    await Utils.clickBtn("Order");
    await Utils.checkConfirmationPage();
    await Utils.clickBtn("Ok");
    await Utils.clickBtn("Order Now");
    await Utils.clickProduct("Fanta");
    await Utils.checkOrderTotal("2.53");
    await Utils.checkProductQty("Fanta", "1");
    await Utils.clickBtn("Checkout");
    await Utils.checkProductInCart("Fanta", "2.53", "1");
    await Utils.clickBtn("Order");
    await Utils.checkConfirmationPage();
    await Utils.clickBtn("Ok");
    await Utils.clickBtn("My Order");
    await Utils.checkIsNoBtn("Order");
    await Utils.clickBackFromCart();
    await Utils.checkBtn("Order Now");
});

test("self_mobile_meal_counter_takeaway_out: meal counter with name/phone", async () => {
    await setupSelfPosEnv("mobile", "counter", "meal", {}, true);
    await Utils.checkIsNoBtn("My Order");
    await Utils.clickOrderNow();
    await Utils.selectLocation("Test-Takeout");
    await Utils.clickProduct("Coca-Cola");
    await Utils.checkOrderTotal("2.53");
    await Utils.checkProductQty("Coca-Cola", "1");
    await Utils.clickBtn("Checkout");
    await Utils.checkProductInCart("Coca-Cola", "2.53", "1");
    await Utils.clickBtn("Order");
    await Utils.fillInput("Name", "Dr Dre");
    await Utils.fillInput("Phone", "490904390");
    await Utils.clickBtn("Continue");
    await Utils.checkConfirmationPage();
    await Utils.clickBtn("Ok");
    await Utils.clickBtn("Order Now");
    await Utils.clickProduct("Fanta");
    await Utils.checkOrderTotal("2.53");
    await Utils.checkProductQty("Fanta", "1");
    await Utils.clickBtn("Checkout");
    await Utils.checkProductInCart("Fanta", "2.53", "1");
    await Utils.clickBtn("Order");
    await Utils.checkConfirmationPage();
    await Utils.clickBtn("Ok");
    await Utils.clickBtn("My Order");
    await Utils.checkIsNoBtn("Order");
    await Utils.clickBackFromCart();
    await Utils.checkBtn("Order Now");
});

test("self_order_mobile_meal_cancel: meal mode cancel and re-order", async () => {
    await setupSelfPosEnv("mobile", "counter", "meal", {}, true);
    await Utils.checkIsNoBtn("My Order");
    await Utils.clickOrderNow();
    await Utils.selectLocation("Test-Takeout");
    await Utils.clickProduct("Coca-Cola");
    await Utils.checkOrderTotal("2.53");
    await Utils.checkProductQty("Coca-Cola", "1");
    await Utils.clickBtn("Checkout");
    await Utils.checkProductInCart("Coca-Cola", "2.53", "1");
    await Utils.clickBackFromCart();
    await Utils.clickCancelFromProductList();
    await Utils.clickBtn("Order Now");
    await Utils.selectLocation("Test-Takeout");
    await Utils.clickProduct("Coca-Cola");
    await Utils.checkOrderTotal("2.53");
    await Utils.checkProductQty("Coca-Cola", "1");
    await Utils.clickBtn("Checkout");
    await Utils.checkProductInCart("Coca-Cola", "2.53", "1");
    await Utils.clickBtn("Order");
    await Utils.fillInput("Name", "Dr Dre");
    await Utils.fillInput("Phone", "490904390");
    await Utils.clickBtn("Continue");
    await Utils.checkConfirmationPage();
    await Utils.clickBtn("Ok");
    await Utils.clickBtn("Order Now");
    await Utils.clickProduct("Fanta");
    await Utils.checkOrderTotal("2.53");
    await Utils.checkProductQty("Fanta", "1");
    await Utils.clickBtn("Checkout");
    await Utils.clickBackFromCart();
    await Utils.clickCancelFromProductList();
    await Utils.clickBtn("My Order");
    await Utils.checkProductInCart("Coca-Cola", "2.53", "1");
    await Utils.checkIsNoBtn("Order");
});

test("self_order_mobile_each_cancel: each mode cancel and re-order", async () => {
    await setupSelfPosEnv("mobile", "counter", "each", {}, true);
    await Utils.checkIsNoBtn("My Order");
    await Utils.clickOrderNow();
    await Utils.selectLocation("Test-Takeout");
    await Utils.clickProduct("Coca-Cola");
    await Utils.clickBtn("Checkout");
    await Utils.checkProductInCart("Coca-Cola", "2.53", "1");
    await Utils.clickBackFromCart();
    await Utils.clickCancelFromProductList();
    await Utils.clickBtn("Order Now");
    await Utils.selectLocation("Test-Takeout");
    await Utils.checkIsDisabledBtn("Checkout");
    await Utils.clickProduct("Fanta");
    await Utils.clickBtn("Checkout");
    await Utils.checkProductInCart("Fanta", "2.53", "1");
    await Utils.clickBtn("Order");
    await Utils.fillInput("Name", "Dr Dre");
    await Utils.fillInput("Phone", "490904390");
    await Utils.clickBtn("Continue");
    await Utils.clickBtn("Ok");
    await Utils.checkIsNoBtn("Order Now");
    await Utils.clickBtn("My Order");
    await Utils.checkProductInCart("Fanta", "2.53", "1");
    await Utils.checkIsNoBtn("Order");
});

test("SelfOrderOrderNumberTour: table selection popup", async () => {
    await setupSelfPosEnv(
        "mobile",
        "table",
        "each",
        { use_presets: false, available_preset_ids: [] },
        true
    );
    await Utils.checkIsNoBtn("My Order");
    await Utils.clickOrderNow();
    await Utils.clickProduct("Coca-Cola");
    await Utils.clickBtn("Checkout");
    await Utils.clickBtn("Order");
    await Utils.selectFloor("Patio");
    await Utils.selectTable("101");
    await Utils.clickBtn("Ok");
    await Utils.checkIsNoBtn("Ok");
});

test("self_mobile_auto_table_selection_takeaway_in: auto table, no table selector", async () => {
    await setupSelfPosEnv("mobile", "table", "each", {}, true);
    await Utils.checkIsNoBtn("My Order");
    await Utils.clickOrderNow();
    await Utils.selectLocation("In");
    await Utils.clickProduct("Coca-Cola");
    await Utils.clickBtn("Checkout");
    await Utils.checkProductInCart("Coca-Cola", "2.53", "1");
    await Utils.clickBtn("Order");
    await Utils.checkNoTableSelector();
    await Utils.checkConfirmationPage();
    await Utils.clickBtn("Ok");
    await Utils.checkIsNoBtn("Order Now");
});

test("self_order_mobile_0_price_order: zero-price with order note", async () => {
    await setupSelfPosEnv("mobile", "table", "each", {}, true);
    await Utils.checkIsNoBtn("My Order");
    await Utils.clickOrderNow();
    await Utils.selectLocation("In");
    await Utils.clickProduct("Ketchup");
    await Utils.clickBtn("Checkout");
    await Utils.checkProductInCart("Ketchup", "0", "1");
    await Utils.clickOrderNoteBtn();
    await Utils.clickTextArea();
    await Utils.typeNote("test");
    await Utils.clickBtn("Apply");
    await Utils.clickBtn("Order");
    await Utils.checkConfirmationPage();
    await Utils.clickBtn("Ok");
    await Utils.clickBtn("My Order");
});

test("test_sub_categories_products_displayed: parent/child category products", async () => {
    await setupSelfPosEnv(
        "kiosk",
        "counter",
        "each",
        {
            limit_categories: true,
            iface_available_categ_ids: [200, 206, 207],
            use_presets: false,
            available_preset_ids: [],
        },
        true
    );
    await Utils.clickOrderNow();
    await Utils.clickCategory("Miscellaneous");
    await Utils.clickProduct("Coca-Cola");
    await Utils.clickCategory("Parent");
    await Utils.clickProduct("Fanta");
});

test("test_sub_categories_products_displayed_mobile: mobile sub categories", async () => {
    await setupSelfPosEnv(
        "mobile",
        "counter",
        "each",
        {
            limit_categories: true,
            iface_available_categ_ids: [200, 206, 207],
            use_presets: false,
            available_preset_ids: [],
        },
        true
    );
    await Utils.checkIsNoBtn("My Order");
    await Utils.clickOrderNow();
    await Utils.clickCategory("Miscellaneous");
    await Utils.clickProduct("Coca-Cola");
    await Utils.clickCategory("Parent");
    await Utils.clickProduct("Fanta");
});

test("test_sub_categories_products_displayed_consultation: consultation sub categories", async () => {
    await setupSelfPosEnv(
        "consultation",
        "counter",
        "each",
        {
            limit_categories: true,
            iface_available_categ_ids: [200, 206, 207],
            use_presets: false,
            available_preset_ids: [],
        },
        true
    );
    await Utils.clickOrderNow();
    await Utils.clickCategory("Miscellaneous");
    await Utils.clickProduct("Coca-Cola");
    await Utils.clickCategory("Parent");
    await Utils.clickProduct("Fanta");
});

test("test_mobile_self_order_preparation_changes: preparation with table select", async () => {
    await setupSelfPosEnv(
        "mobile",
        "table",
        "each",
        { use_presets: false, available_preset_ids: [] },
        true
    );
    await Utils.checkIsNoBtn("My Order");
    await Utils.clickOrderNow();
    await Utils.clickProduct("Coca-Cola");
    await Utils.clickProduct("Fanta");
    await Utils.clickBtn("Checkout");
    await Utils.checkProductInCart("Fanta", "2.53", "1");
    await Utils.checkProductInCart("Coca-Cola", "2.53", "1");
    await Utils.clickBtn("Order");
    await Utils.selectTable("1");
    await Utils.checkConfirmationPage();
    await Utils.clickBtn("Ok");
});

test("test_self_order_kiosk_product_availability: kiosk unavailable product handling", async () => {
    const store = await setupSelfPosEnv("kiosk", "table", "each", {}, true);
    const officeComboTemplate = store.models["product.template"].get(230);
    officeComboTemplate.combo_ids = [store.models["product.combo"].get(201)];
    await Utils.clickOrderNow();
    await Utils.selectLocation("Dine in");
    await Utils.clickCategory("Combos");
    await Utils.setProductAvailability(store, "Combo Product 5", false);
    await Utils.isProductNotDisplayed("Combo Product 5");
    await Utils.clickProduct("Office Combo");
    await Utils.clickComboProduct("Combo Product 4");
    await Utils.clickBtn("Next");
    await Utils.clickBtn("Add to cart");
    await Utils.clickBtn("Checkout");
    await Utils.setProductAvailability(store, "Office Combo", false);
    await Utils.clickBtn("Order");
    await Utils.dialogBodyIs(
        "It seems that Office Combo is no longer available. Please go back and edit your order."
    );
    await Utils.confirmDialog("OK");
    await Utils.clickOrderNow();
    await Utils.selectLocation("Dine in");
    await Utils.clickCategory("Combos");
    await Utils.clickProduct("Combo Product 4");
    await Utils.setProductAvailability(store, "Combo Product 5", true);
    await Utils.clickProduct("Combo Product 5");
    await Utils.clickBtn("Checkout");
    await Utils.setProductAvailability(store, "Combo Product 5", false);
    await Utils.clickBtn("Order");
    await Utils.dialogBodyIs(
        "It seems that Combo Product 5 is no longer available. Please go back and edit your order."
    );
    await Utils.confirmDialog("OK");
    await Utils.clickBtn("Order");
    await Utils.clickNumpad("3");
    await Utils.clickBtn("Order");
    await Utils.clickBtn("Close");
});

test("test_self_order_product_availability: mobile unavailable product handling", async () => {
    const store = await setupSelfPosEnv("mobile", "table", "each", {}, true);
    mockDate("2025-07-29 12:00:00");
    const officeComboTemplate = store.models["product.template"].get(230);
    officeComboTemplate.combo_ids = [store.models["product.combo"].get(201)];
    const snooze = store.models["pos.snooze"].create({
        product_template_id: 221,
        pos_config_id: 1,
        start_time: "2025-07-29 00:00:00",
        end_time: "2025-07-30 00:00:00",
    });
    store.config.pos_snooze_ids = [snooze, ...(store.config.pos_snooze_ids || [])];
    store.snoozeTracker.setSnoozes(store.config.pos_snooze_ids);
    await Utils.checkIsNoBtn("My Order");
    await Utils.clickOrderNow();
    await Utils.selectLocation("In");
    await Utils.isProductDisplayed("Combo Product 2", true);
    await Utils.setProductAvailability(store, "Combo Product 5", false);
    await Utils.isProductNotDisplayed("Combo Product 5");
    await Utils.clickProduct("Office Combo");
    await Utils.clickComboProduct("Combo Product 4");
    await Utils.clickBtn("Next");
    await Utils.clickBtn("Add to cart");
    await Utils.clickBtn("Checkout");
    await Utils.setProductAvailability(store, "Office Combo", false);
    await Utils.clickBtn("Order");
    await Utils.dialogBodyIs(
        "It seems that Office Combo is no longer available. Please go back and edit your order."
    );
    await Utils.confirmDialog("OK");
    await Utils.clickOrderNow();
    await Utils.clickProduct("Combo Product 4");
    await Utils.setProductAvailability(store, "Combo Product 5", true);
    await Utils.clickProduct("Combo Product 5");
    await Utils.clickBtn("Checkout");
    await Utils.setProductAvailability(store, "Combo Product 5", false);
    await Utils.clickBtn("Order");
    await Utils.dialogBodyIs(
        "It seems that Combo Product 5 is no longer available. Please go back and edit your order."
    );
    await Utils.confirmDialog("OK");
    await Utils.clickBtn("Order");
    await Utils.clickBtn("Ok");
});

test("self_multi_attribute_selector: multi-check attribute selection", async () => {
    const store = await setupSelfPosEnv("mobile", "counter", "each", {}, true);
    const fabricAttr = store.models["product.attribute"].get(201);
    fabricAttr.display_type = "multi";
    await Utils.clickOrderNow();
    await Utils.selectLocation("In");
    await Utils.clickProduct("Desk Organizer");
    await Utils.setupAttribute([
        { name: "Fabric", value: "Leather" },
        { name: "Fabric", value: "Custom" },
    ]);
    Utils.checkAttributeShown("Fabric");
    Utils.checkAttributeGroups(2, 2);
    Utils.checkAttributeGroupHasValues(["Leather", "Custom"]);
});

test("test_self_order_pricelist: kiosk pricelist with fixed price", async () => {
    const store = await setupSelfPosEnv(
        "kiosk",
        "counter",
        "each",
        { use_presets: false, available_preset_ids: [], use_pricelist: true },
        true
    );
    const colaTmpl = store.models["product.template"].get(200);
    const pricelistId = store.models["product.pricelist"].create({
        name: "Test pricelist",
    });
    store.models["product.pricelist.item"].create({
        compute_price: "fixed",
        fixed_price: 1,
        min_quantity: 3,
        product_tmpl_id: colaTmpl.id,
        pricelist_id: pricelistId,
    });

    store.config.pricelist_id = pricelistId;
    store.config.available_pricelist_ids = [pricelistId];
    store.initProducts();
    await Utils.checkIsNoBtn("My Order");
    await Utils.clickOrderNow();
    await Utils.clickCategory("Miscellaneous");
    await Utils.clickProduct("Coca-Cola");
    await Utils.clickProduct("Coca-Cola");
    await Utils.clickBtn("Checkout");
    await Utils.checkProductInCart("Coca-Cola", "5.06", "2");
    await Utils.clickBackFromCart();
    await Utils.clickProduct("Coca-Cola");
    await Utils.clickBtn("Checkout");
    await Utils.checkProductInCart("Coca-Cola", "3.00", "3");
    await Utils.clickBtn("Order");
    await Utils.clickBtn("Close");
    await Utils.checkIsNoBtn("My Order");
});

test("self_order_mobile_special_products_category: special products category hidden", async () => {
    await setupSelfPosEnv(
        "mobile",
        "counter",
        "each",
        {
            limit_categories: true,
            iface_available_categ_ids: [208],
        },
        true
    );
    await Utils.checkIsNoBtn("My Order");
    await Utils.clickOrderNow();
    await Utils.selectLocation("Test-Takeout");
    await Utils.checkCategoryBtn("MOOL");
    Utils.checkIsNoCategoryBtn("Specials");
    await Utils.isProductNotDisplayed("Special 1");
});

test("self_order_hidden_category: hidden category is out of the menu but stays in combos", async () => {
    const store = await setupSelfPosEnv("mobile", "counter", "each", {}, true);
    store.models["pos.category"].get(200).self_order_available = false;
    store.initProducts();
    store.computeAvailableCategories();
    await Utils.clickOrderNow();
    await Utils.selectLocation("Test-Takeout");
    Utils.checkIsNoCategoryBtn("Miscellaneous");
    await Utils.isProductNotDisplayed("Combo Product 1");
    // The products of a hidden category remain selectable as combo choices.
    await Utils.clickCategory("Combos");
    await Utils.clickProduct("Office Combo");
    await Utils.isProductDisplayed("Combo Product 1");
});

test("self_order_hidden_child_category: hidden child category is out of the kiosk menu", async () => {
    const store = await setupSelfPosEnv(
        "kiosk",
        "counter",
        "each",
        {
            limit_categories: true,
            iface_available_categ_ids: [203, 204, 205],
            use_presets: false,
            available_preset_ids: [],
        },
        true
    );
    store.models["pos.category"].get(205).self_order_available = false;
    store.initProducts();
    store.computeAvailableCategories();
    await Utils.clickOrderNow();
    await Utils.clickChildCategory("Test Child Category 1");
    Utils.checkIsNoChildCategoryBtn("Test Child Category 2");
});

test("self_order_restricted_child_category: the parent of a restricted category is displayed", async () => {
    await setupSelfPosEnv(
        "kiosk",
        "counter",
        "each",
        {
            limit_categories: true,
            iface_available_categ_ids: [204],
            use_presets: false,
            available_preset_ids: [],
        },
        true
    );
    await Utils.clickOrderNow();
    // "Test Child Category 1" is the only available category, it is reached through its parent.
    await Utils.checkCategoryBtn("Test Category");
    Utils.checkIsNoChildCategoryBtn("Test Child Category 2");
    // The parent only gives access to the products of the available child category.
    await Utils.isProductNotDisplayed("Pepsi");
    await Utils.clickChildCategory("Test Child Category 1");
    await Utils.clickProduct("Coca-Cola");
});

test("self_order_mobile_no_access_token: no access token hides order button", async () => {
    const store = await setupSelfPosEnv("mobile", "table", "each", {}, true);
    store.access_token = null;
    await Utils.checkIsNoBtn("My Order");
    await Utils.clickOrderNow();
    await Utils.selectLocation("Test-Takeout");
    await Utils.checkIsNoBtn("Order");
});

test("self_order_preset_dine_in_tour: dine in preset with table identifier", async () => {
    await setupSelfPosEnv("mobile", "table", "each", {}, true);
    patchWithCleanup(SelfOrderRouter.prototype, {
        getTableIdentifier() {
            return "2";
        },
    });
    await Utils.checkIsNoBtn("My Order");
    await Utils.clickOrderNow();
    await Utils.selectLocation("Dine in");
    await Utils.clickProduct("Coca-Cola");
    await Utils.clickBtn("Checkout");
    await Utils.checkProductInCart("Coca-Cola", "2.53", "1");
    await Utils.clickBtn("Order");
    await Utils.clickBtn("Ok");
});

test("test_slot_limit_orders: slot limit order test", async () => {
    await mockDate("2023-07-30 00:00:00");
    const store = await setupSelfPosEnv("kiosk", "counter", "each", {}, true);
    const preset = store.models["pos.preset"].get(2);
    preset.identification = "name";
    preset.slots_per_interval = 1;
    await Utils.clickOrderNow();
    await Utils.selectLocation("Out");
    await Utils.clickCategory("Miscellaneous");
    await Utils.clickProduct("Free");
    await Utils.clickBtn("Checkout");
    await Utils.clickBtn("Order");
    await Utils.selectSpecificSlot("12:00");
    await Utils.fillInput("Name", "Dr Dre");
    await Utils.fillInput("Phone", "490904390");
    await Utils.clickBtn("Continue");
    await Utils.clickBtn("Close");
    await Utils.clickOrderNow();
    await Utils.selectLocation("Out");
    await store.syncPresetSlotAvaibility(preset);
    await Utils.clickCategory("Miscellaneous");
    await Utils.clickProduct("Free");
    await Utils.clickBtn("Checkout");
    await Utils.clickBtn("Order");
    await Utils.checkSlotUnavailable("12:00");
});

test("test_self_order_preset_btn: check preset button displays correct preset", async () => {
    await setupSelfPosEnv("kiosk", "counter", "each", {}, true);
    await Utils.checkIsNoBtn("My Order");
    await Utils.clickBtn("Order Now");
    await Utils.selectLocation("Takeaway");
    await Utils.clickCategory("Miscellaneous");
    await Utils.clickProduct("Coca-Cola");
    await Utils.clickBtn("Checkout");
    await Utils.checkPreset("Takeaway");
    await Utils.clickPresetBtn();
    await Utils.selectLocation("Delivery");
    await Utils.isCartPageShown();
    await Utils.checkPreset("Delivery");
});
