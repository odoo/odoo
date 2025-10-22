import { registry } from "@web/core/registry";
import * as Utils from "@pos_self_order/../tests/tours/utils/common";
import * as CartPage from "@pos_self_order/../tests/tours/utils/cart_page_util";
import * as ConfirmationPage from "@pos_self_order/../tests/tours/utils/confirmation_page_util";
import * as LandingPage from "@pos_self_order/../tests/tours/utils/landing_page_util";
import * as ProductPage from "@pos_self_order/../tests/tours/utils/product_page_util";
import * as Numpad from "@point_of_sale/../tests/generic_helpers/numpad_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";

registry.category("web_tour.tours").add("self_kiosk_each_table_takeaway_in", {
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        ProductPage.clickCategory("Miscellaneous"),
        ProductPage.checkReferenceNotInProductName("Coca-Cola", "12345"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Checkout"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        Utils.clickBtn("Order"),
        Numpad.click("3"),
        Utils.clickBtn("Order"),
        ConfirmationPage.orderNumberShown(),
        ConfirmationPage.orderNumberIs("K", "3"),
        Utils.clickBtn("Close"),
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        ProductPage.clickCategory("Miscellaneous"),
        Utils.checkIsDisabledBtn("Checkout"),
    ],
});

registry.category("web_tour.tours").add("self_kiosk_each_table_takeaway_out", {
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        ProductPage.clickCategory("Miscellaneous"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Checkout"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        Utils.clickBtn("Order"),
        Utils.clickBtn("Close"),
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        ProductPage.clickCategory("Miscellaneous"),
        Utils.checkIsDisabledBtn("Checkout"),
    ],
});

registry.category("web_tour.tours").add("self_kiosk_each_counter_takeaway_in", {
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Test-In"),
        ProductPage.clickCategory("Miscellaneous"),
        ProductPage.clickProduct("Coca-Cola"),
        ProductPage.clickCategory("Uncategorised"),
        ProductPage.clickProduct("Yummy Burger"),
        ProductPage.clickProduct("Taxi Burger"),
        Utils.clickBtn("Checkout"),
        CartPage.checkProduct("Coca-Cola", "2.53"),
        CartPage.checkProduct("Yummy Burger", "10"),
        CartPage.checkProduct("Taxi Burger", "11"),
        CartPage.checkTotalPrice("23.53"),
        Utils.clickBtn("Order"),
        Numpad.click("3"),
        Utils.clickBtn("Order"),
        Utils.clickBtn("Close"),
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Test-In"),
        ProductPage.clickCategory("Miscellaneous"),
        Utils.checkIsDisabledBtn("Checkout"),
    ],
});

registry.category("web_tour.tours").add("self_kiosk_each_counter_takeaway_out", {
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Test-Takeout"),
        ProductPage.clickCategory("Miscellaneous"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Checkout"),
        CartPage.checkProduct("Coca-Cola", "2.53"),
        Utils.clickBtn("Order"),
        CartPage.fillInput("Name", "Mr Kiosk"),
        Utils.clickBtn("Continue"),
        Utils.clickBtn("Close"),
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Test-Takeout"),
        ProductPage.clickCategory("Miscellaneous"),
        Utils.checkIsDisabledBtn("Checkout"),
    ],
});

registry.category("web_tour.tours").add("self_order_kiosk_cancel", {
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        ProductPage.clickCategory("Miscellaneous"),
        ProductPage.clickProduct("Coca-Cola"),
        ProductPage.clickProduct("Fanta"),
        Utils.clickBtn("Checkout"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        CartPage.checkProduct("Fanta", "2.53", "1"),
        CartPage.clickBack(),
        ...ProductPage.clickCancel(),
        Utils.clickBtn("Order Now"),
        ProductPage.clickCategory("Miscellaneous"),
        Utils.checkIsDisabledBtn("Checkout"),
    ],
});

registry.category("web_tour.tours").add("kiosk_simple_order", {
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Checkout"),
        CartPage.checkProduct("Coca-Cola", "2.53"),
        Utils.clickBtn("Order"),
        Utils.clickBtn("Close"),
        Utils.checkIsNoBtn("My Order"),
    ],
});

registry.category("web_tour.tours").add("kiosk_order_price_null", {
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Checkout"),
        CartPage.checkProduct("Coca-Cola", "0.00"),
        Utils.clickBtn("Order"),
        ConfirmationPage.orderNumberShown(),
        Utils.checkBtn("Close"),
    ],
});

registry.category("web_tour.tours").add("self_order_language_changes", {
    steps: () => [
        LandingPage.checkLanguageSelected("English"),
        LandingPage.checkCountryFlagShown("us"),

        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Test-Takeout"),
        ProductPage.clickCategory("Test Category"),
        ProductPage.clickProduct("Test Product"),
        ...ProductPage.clickCancel(),
        LandingPage.checkLanguageSelected("English"),
        LandingPage.checkCountryFlagShown("us"),
        ...Utils.changeLanguage("Français"),

        Utils.clickBtn("Commander maintenant"),
        LandingPage.selectLocation("Test-Takeout"),
        ProductPage.clickCategory("Catégorie Test"),
        ProductPage.clickProduct("Produit Test"),
    ],
});

registry.category("web_tour.tours").add("test_self_order_kiosk_combo_sides", {
    steps: () => [
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Test-In"),
        ProductPage.clickCategory("Uncategorised"),
        ProductPage.clickProduct("Office Combo"),
        ProductPage.clickComboProduct("Desk Organizer"),
        {
            trigger: `button:disabled:contains("Next")`,
        },
        ...ProductPage.setupAttribute([
            { name: "Size", value: "M" },
            { name: "Fabric", value: "Leather" },
        ]),
        Utils.clickBtn("Add to cart"),
    ],
});

registry.category("web_tour.tours").add("test_self_order_kiosk_combo_qty_max_free", {
    steps: () => [
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Test-In"),
        ProductPage.clickCategory("Category 2"),
        ProductPage.clickProduct("Office Combo"),
        ProductPage.clickComboProduct("Combo Product 4"),
        ...Utils.increaseComboItemQty("Combo Product 4", 3),
        Utils.clickBtn("Next"),
        Utils.clickBtn("Add to cart"),
    ],
});

registry.category("web_tour.tours").add("test_self_order_pricelist", {
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        ProductPage.clickCategory("Miscellaneous"),
        ProductPage.clickProduct("Coca-Cola"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Checkout"),
        CartPage.checkProduct("Coca-Cola", "5.06", "2"),
        CartPage.clickBack(),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Checkout"),
        CartPage.checkProduct("Coca-Cola", "3.45", "3"),
        Utils.clickBtn("Order"),
        Utils.clickBtn("Close"),
        Utils.checkIsNoBtn("My Order"),
    ],
});

registry.category("web_tour.tours").add("test_self_order_kiosk_product_availability", {
    steps: () => [
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Test-In"),
        ProductPage.clickCategory("Category 2"),
        // Mark 'Combo Product 5' as unavailable and verify it shows as out of stock
        Utils.setProductAvailability("Combo Product 5", false),
        ProductPage.checkProductOutOfStock("Combo Product 5"),
        ProductPage.clickProduct("Office Combo"),
        ProductPage.clickComboProduct("Combo Product 4"),
        Utils.clickBtn("Add to cart"),
        // Make 'Office Combo' unavailable and attempt payment
        // Expect a dialog stating the product is no longer available and user is redirected to product page
        Utils.clickBtn("Checkout"),
        Utils.setProductAvailability("Office Combo", false),
        Utils.clickBtn("Order"),
        Dialog.bodyIs(
            "It seems that Office Combo is no longer available. Please go back and edit your order."
        ),
        Dialog.confirm("OK"),
        // Add 'Combo Product 4' again and mark 'Combo Product 5' available, then unavailable after adding to cart
        // Expect unavailable product dialog and user should remain on cart page to process remaining items
        ProductPage.clickProduct("Combo Product 4"),
        Utils.setProductAvailability("Combo Product 5", true),
        ProductPage.clickProduct("Combo Product 5"),
        Utils.clickBtn("Checkout"),
        Utils.setProductAvailability("Combo Product 5", false),
        Utils.clickBtn("Order"),
        Dialog.bodyIs(
            "It seems that Combo Product 5 is no longer available. Please go back and edit your order."
        ),
        Dialog.confirm("OK"),
        Utils.clickBtn("Order"),
        Numpad.click("3"),
        Utils.clickBtn("Order"),
        Utils.clickBtn("Close"),
    ],
});

registry.category("web_tour.tours").add("test_self_order_parent_category", {
    steps: () => [
        Utils.clickBtn("Order Now"),
        ProductPage.clickChildCategory("Test Child Category 1"),
        ProductPage.clickProduct("Coca-Cola"),
        ProductPage.clickChildCategory("Test Child Category 2"),
        ProductPage.clickProduct("Pepsi"),
        Utils.clickBtn("Checkout"),
        Utils.clickBtn("Order"),
        Utils.clickBtn("Close"),
    ],
});
