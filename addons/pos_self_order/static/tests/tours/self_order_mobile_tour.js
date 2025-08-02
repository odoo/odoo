import { registry } from "@web/core/registry";
import * as Utils from "@pos_self_order/../tests/tours/utils/common";
import * as CartPage from "@pos_self_order/../tests/tours/utils/cart_page_util";
import * as LandingPage from "@pos_self_order/../tests/tours/utils/landing_page_util";
import * as ProductPage from "@pos_self_order/../tests/tours/utils/product_page_util";
import * as ConfirmationPage from "@pos_self_order/../tests/tours/utils/confirmation_page_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";

registry.category("web_tour.tours").add("self_mobile_each_table_takeaway_in", {
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Test-In"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Checkout"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        Utils.clickBtn("Order"),
        ...CartPage.selectTable("3"),
        Utils.clickBtn("Ok"),
        Utils.checkIsNoBtn("Order Now"),
        Utils.clickBtn("My Order"),
        Utils.clickBtn("Order"),
        Utils.clickBtn("Ok"),
        Utils.checkIsNoBtn("Order Now"),
        Utils.clickBtn("My Order"),
        ...CartPage.cancelOrder(),
        Utils.checkBtn("Order Now"),
        Utils.checkBtn("My Orders"),
    ],
});

registry.category("web_tour.tours").add("self_mobile_each_table_takeaway_out", {
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Test-Takeout"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Checkout"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        Utils.clickBtn("Order"),
        CartPage.fillInput("Name", "Dr Dre"),
        Utils.clickBtn("Continue"),
        Utils.clickBtn("Ok"),
        Utils.checkIsNoBtn("Order Now"),
        Utils.clickBtn("My Order"),
        Utils.clickBtn("Order"),
        Utils.clickBtn("Ok"),
        Utils.checkIsNoBtn("Order Now"),
    ],
});

registry.category("web_tour.tours").add("self_mobile_each_counter_takeaway_in", {
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Test-In"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Checkout"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        Utils.clickBtn("Order"),
        ...CartPage.selectTable("3"),
        Utils.clickBtn("Ok"),
        Utils.checkIsNoBtn("Order Now"),
        Utils.clickBtn("My Order"),
        Utils.clickBtn("Order"),
        Utils.clickBtn("Ok"),
        Utils.checkIsNoBtn("Order Now"),
    ],
});

registry.category("web_tour.tours").add("self_mobile_each_counter_takeaway_out", {
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Test-Takeout"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Checkout"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        Utils.clickBtn("Order"),
        CartPage.fillInput("Name", "Dr Dre"),
        Utils.clickBtn("Continue"),
        Utils.clickBtn("Ok"),
        Utils.checkIsNoBtn("Order Now"),
        Utils.clickBtn("My Order"),
        Utils.clickBtn("Order"),
        Utils.clickBtn("Ok"),
        Utils.checkIsNoBtn("Order Now"),
    ],
});

registry.category("web_tour.tours").add("self_mobile_meal_table_takeaway_in", {
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Test-In"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Checkout"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        Utils.clickBtn("Order"),
        ...CartPage.selectTable("3"),
        Utils.clickBtn("Ok"),
        Utils.clickBtn("Order Now"),
        ProductPage.clickProduct("Fanta"),
        Utils.clickBtn("Checkout"),
        CartPage.checkProduct("Fanta", "2.53", "1"),
        Utils.clickBtn("Order"),
        ConfirmationPage.isShown(),
        Utils.clickBtn("Ok"),
        Utils.clickBtn("My Order"),
        Utils.clickBtn("Order"),
        Utils.clickBtn("Ok"),
        Utils.checkBtn("Order Now"),
    ],
});

registry.category("web_tour.tours").add("self_mobile_meal_table_takeaway_out", {
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Test-Takeout"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Checkout"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        Utils.clickBtn("Order"),
        CartPage.fillInput("Name", "Dr Dre"),
        Utils.clickBtn("Continue"),
        ConfirmationPage.isShown(),
        Utils.clickBtn("Ok"),
        Utils.clickBtn("Order Now"),
        ProductPage.clickProduct("Fanta"),
        Utils.clickBtn("Checkout"),
        CartPage.checkProduct("Fanta", "2.53", "1"),
        Utils.clickBtn("Order"),
        ConfirmationPage.isShown(),
        Utils.clickBtn("Ok"),
        Utils.clickBtn("My Order"),
        Utils.clickBtn("Order"),
        Utils.clickBtn("Ok"),
        Utils.checkBtn("Order Now"),
    ],
});

registry.category("web_tour.tours").add("self_mobile_meal_counter_takeaway_in", {
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Test-In"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Checkout"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        Utils.clickBtn("Order"),
        ...CartPage.selectTable("3"),
        ConfirmationPage.isShown(),
        Utils.clickBtn("Ok"),
        Utils.clickBtn("Order Now"),
        ProductPage.clickProduct("Fanta"),
        Utils.clickBtn("Checkout"),
        CartPage.checkProduct("Fanta", "2.53", "1"),
        Utils.clickBtn("Order"),
        ConfirmationPage.isShown(),
        Utils.clickBtn("Ok"),
        Utils.clickBtn("My Order"),
        Utils.clickBtn("Order"),
        Utils.clickBtn("Ok"),
        Utils.checkBtn("Order Now"),
    ],
});

registry.category("web_tour.tours").add("self_mobile_meal_counter_takeaway_out", {
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Test-Takeout"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Checkout"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        Utils.clickBtn("Order"),
        CartPage.fillInput("Name", "Dr Dre"),
        Utils.clickBtn("Continue"),
        ConfirmationPage.isShown(),
        Utils.clickBtn("Ok"),
        Utils.clickBtn("Order Now"),
        ProductPage.clickProduct("Fanta"),
        Utils.clickBtn("Checkout"),
        CartPage.checkProduct("Fanta", "2.53", "1"),
        Utils.clickBtn("Order"),
        ConfirmationPage.isShown(),
        Utils.clickBtn("Ok"),
        Utils.clickBtn("My Order"),
        Utils.clickBtn("Order"),
        Utils.clickBtn("Ok"),
        Utils.checkBtn("Order Now"),
    ],
});

registry.category("web_tour.tours").add("self_order_mobile_meal_cancel", {
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Test-Takeout"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Checkout"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        CartPage.clickBack(),
        ...ProductPage.clickCancel(),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Test-Takeout"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Checkout"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        Utils.clickBtn("Order"),
        CartPage.fillInput("Name", "Dr Dre"),
        Utils.clickBtn("Continue"),
        ConfirmationPage.isShown(),
        Utils.clickBtn("Ok"),
        Utils.clickBtn("Order Now"),
        ProductPage.clickProduct("Fanta"),
        Utils.clickBtn("Checkout"),
        CartPage.clickBack(),
        ...ProductPage.clickCancel(),
        Utils.clickBtn("My Order"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        Utils.checkBtn("Order"),
    ],
});

registry.category("web_tour.tours").add("self_order_mobile_each_cancel", {
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Test-Takeout"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Checkout"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        CartPage.clickBack(),
        ...ProductPage.clickCancel(),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Test-Takeout"),
        Utils.checkIsDisabledBtn("Checkout"),
        ProductPage.clickProduct("Fanta"),
        Utils.clickBtn("Checkout"),
        CartPage.checkProduct("Fanta", "2.53", "1"),
        Utils.clickBtn("Order"),
        CartPage.fillInput("Name", "Dr Dre"),
        Utils.clickBtn("Continue"),
        Utils.clickBtn("Ok"),
        Utils.checkIsNoBtn("Order Now"),
        Utils.clickBtn("My Order"),
        CartPage.checkProduct("Fanta", "2.53", "1"),
        Utils.checkBtn("Order"),
    ],
});

registry.category("web_tour.tours").add("SelfOrderOrderNumberTour", {
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Checkout"),
        Utils.clickBtn("Order"),
        ...CartPage.selectTable("101"),
        Utils.clickBtn("Ok"),
        Utils.checkIsNoBtn("Ok"),
    ],
});

registry.category("web_tour.tours").add("self_order_mobile_special_products_category", {
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Test-Takeout"),
        {
            content: "Category 'Miscellaneous' is displayed",
            trigger: ".category_btn:contains('Miscellaneous')",
        },
        {
            content: "Category 'Specials' is not displayed",
            trigger: ".category_btn:not(:contains('Specials'))",
        },
        {
            content: "Product 'Special 1' is not displayed",
            trigger: ".self_order_product_name:not(:contains('Special 1'))",
        },
    ],
});

registry.category("web_tour.tours").add("self_mobile_auto_table_selection_takeaway_in", {
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Test-In"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Checkout"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        Utils.clickBtn("Order"),
        CartPage.checkNoTableSelector(),
        ConfirmationPage.isShown(),
        Utils.clickBtn("Ok"),
        Utils.checkIsNoBtn("Order Now"),
    ],
});

registry.category("web_tour.tours").add("test_self_order_product_availability", {
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Test-In"),
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
        ...CartPage.selectTable("1"),
        Utils.clickBtn("Ok"),
    ],
});

registry.category("web_tour.tours").add("self_order_mobile_0_price_order", {
    steps: () =>
        [
            Utils.checkIsNoBtn("My Order"),
            Utils.clickBtn("Order Now"),
            LandingPage.selectLocation("Test-In"),
            ProductPage.clickProduct("Ketchup"),
            Utils.clickBtn("Checkout"),
            CartPage.checkProduct("Ketchup", "0", "1"),
            Utils.clickBtn("Order"),
            CartPage.selectTable("3"),
            ConfirmationPage.isShown(),
            Utils.clickBtn("Ok"),
            Utils.clickBtn("My Order"),
        ].flat(),
});
