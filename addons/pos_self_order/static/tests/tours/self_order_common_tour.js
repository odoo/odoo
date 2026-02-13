import { registry } from "@web/core/registry";
import * as Utils from "@pos_self_order/../tests/tours/utils/common";
import * as CartPage from "@pos_self_order/../tests/tours/utils/cart_page_util";
import * as ConfirmationPage from "@pos_self_order/../tests/tours/utils/confirmation_page_util";
import * as LandingPage from "@pos_self_order/../tests/tours/utils/landing_page_util";
import * as Numpad from "@point_of_sale/../tests/generic_helpers/numpad_util";
import * as ProductPage from "@pos_self_order/../tests/tours/utils/product_page_util";

registry.category("web_tour.tours").add("self_order_is_close", {
    steps: () => [
        LandingPage.isClosed(),
        Utils.clickBtn("Order Now"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.checkIsNoBtn("Checkout"),
    ],
});

registry.category("web_tour.tours").add("self_order_is_open_consultation", {
    steps: () => [
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Test-Takeout"),
        LandingPage.isOpened(),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.checkIsNoBtn("Order"),
    ],
});

registry.category("web_tour.tours").add("self_order_landing_page_carousel", {
    steps: () => [Utils.checkIsNoBtn("My Order"), LandingPage.checkCarouselAutoPlaying()],
});

registry.category("web_tour.tours").add("self_order_pos_closed", {
    undeterministicTour_doNotCopy: true, // Remove this key to make the tour failed. ( It removes delay between steps )
    steps: () => [
        LandingPage.isClosed(),
        // Normal product
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Test-Takeout"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.checkIsNoBtn("Checkout"),
        // Product with attributes
        ProductPage.clickProduct("Desk Organizer"),
        ...ProductPage.setupAttribute(
            [
                { name: "Size", value: "M" },
                { name: "Fabric", value: "Leather" },
            ],
            false
        ),
        Utils.checkIsNoBtn("Add to cart"),
        ProductPage.clickDiscard(),
        // Combo product
        ProductPage.clickProduct("Office Combo"),
        ...ProductPage.setupCombo(
            [
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
            ],
            false
        ),
        Utils.checkIsNoBtn("Add to cart"),
    ],
});

registry.category("web_tour.tours").add("kiosk_order_pos_closed", {
    undeterministicTour_doNotCopy: true, // Remove this key to make the tour failed. ( It removes delay between steps )
    steps: () => [
        LandingPage.isClosed(),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Test-In"),
        ProductPage.clickCategory("Miscellaneous"),

        ProductPage.clickProduct("Coca-Cola"),
        Utils.checkIsNoBtn("Checkout"),

        // Product with attributes
        ProductPage.clickProduct("Desk Organizer"),
        ...ProductPage.setupAttribute(
            [
                { name: "Size", value: "M" },
                { name: "Fabric", value: "Leather" },
            ],
            false
        ),
        Utils.checkIsNoBtn("Add to cart"),
        ProductPage.clickDiscard(),
        // Combo product
        ProductPage.clickCategory("Category 2"),
        ProductPage.clickProduct("Office Combo"),
        ...ProductPage.setupCombo(
            [
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
            ],
            false
        ),
        Utils.checkIsNoBtn("Add to cart"),
    ],
});

registry.category("web_tour.tours").add("test_self_order_products_sorting_order", {
    steps: () => [
        LandingPage.isClosed(),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Test-Takeout"),
        ProductPage.checkNthProduct(1, "Free"),
        ProductPage.checkNthProduct(2, "Desk Organizer"),
        ProductPage.checkNthProduct(3, "Ketchup"),
        ProductPage.checkNthProduct(4, "Fanta"),
        ProductPage.checkNthProduct(5, "Coca-Cola"),
    ],
});

registry.category("web_tour.tours").add("test_self_order_optional_product", {
    steps: () =>
        [
            Utils.checkIsNoBtn("My Order"),
            Utils.clickBtn("Order Now"),
            ProductPage.clickCategory("Miscellaneous"),
            ProductPage.clickProduct("Coca-Cola"),
            Utils.clickBtn("No Thanks"),
            ProductPage.clickProduct("Coca-Cola"),
            ProductPage.clickOptionalProduct("Fanta"),
            Utils.clickBtn("Continue"),
            ProductPage.clickProduct("Coca-Cola"),
            Utils.clickBtn("No Thanks"),
            ProductPage.clickProduct("Desk Organizer"),
            ProductPage.setupAttribute([
                { name: "Size", value: "M" },
                { name: "Fabric", value: "Leather" },
            ]),
            Utils.clickBtn("Add to cart"),
            ProductPage.clickOptionalProduct("Office Combo"),
            ProductPage.setupCombo([
                {
                    product: "Combo Product 3",
                    attributes: [],
                },
                {
                    product: "Combo Product 5",
                    attributes: [],
                },
                {
                    product: "Combo Product 8",
                    attributes: [],
                },
            ]),
            Utils.clickBtn("Continue"),
            Utils.clickBtn("Checkout"),
            CartPage.checkProduct("Coca-Cola", "7.59", "3"),
            CartPage.checkProduct("Fanta", "2.53", "1"),
            CartPage.checkProduct("Desk Organizer", "5.87", "1"),
            CartPage.checkCombo("Office Combo", [
                {
                    product: "Combo Product 3",
                    attributes: [],
                },
                {
                    product: "Combo Product 5",
                    attributes: [],
                },
                {
                    product: "Combo Product 8",
                    attributes: [],
                },
            ]),
            Utils.clickBtn("Order"),
            Numpad.click("3"),
            Utils.clickBtn("Order"),
            ConfirmationPage.orderNumberShown(),
            Utils.clickBtn("Close"),
        ].flat(),
});
