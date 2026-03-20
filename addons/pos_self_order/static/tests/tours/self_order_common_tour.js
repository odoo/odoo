import { registry } from "@web/core/registry";
import * as Utils from "@pos_self_order/../tests/tours/utils/common";
import * as LandingPage from "@pos_self_order/../tests/tours/utils/landing_page_util";
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
