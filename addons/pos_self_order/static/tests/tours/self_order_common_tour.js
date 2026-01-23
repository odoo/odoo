import { registry } from "@web/core/registry";
import * as Utils from "@pos_self_order/../tests/tours/utils/common";
import * as LandingPage from "@pos_self_order/../tests/tours/utils/landing_page_util";
import * as ProductPage from "@pos_self_order/../tests/tours/utils/product_page_util";
import * as CartPage from "@pos_self_order/../tests/tours/utils/cart_page_util";
import * as ConfirmationPage from "@pos_self_order/../tests/tours/utils/confirmation_page_util";

registry.category("web_tour.tours").add("self_order_is_close", {
    steps: () => [
        LandingPage.isClosed(),
        Utils.clickBtn("Order Now"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.checkIsNoBtn("Order"),
    ],
});

registry.category("web_tour.tours").add("self_order_is_open_consultation", {
    steps: () => [
        Utils.clickBtn("Order Now"),
        LandingPage.isOpened(),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.checkIsNoBtn("Order"),
    ],
});

registry.category("web_tour.tours").add("self_order_landing_page_carousel", {
    steps: () => [Utils.checkIsNoBtn("My Order"), LandingPage.checkCarouselAutoPlaying()],
});

registry.category("web_tour.tours").add("self_order_create_price_on_backend", {
    steps: () => [
        // Normal flow computes the expected price
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Take Out"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Order"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        Utils.clickBtn("Pay"),
        Utils.checkIsNoBtn("Order Now"),
        ConfirmationPage.isShown(),
        ConfirmationPage.checkFinalPrice("$ 2.53"),
        Utils.clickBtn("Close"),

        // Injected price is rejected
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Take Out"),
        ProductPage.clickProduct("Coca-Cola"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Order"),
        CartPage.checkProduct("Coca-Cola", "5.06", "2"),
        {
            content: "Modify the price with javascript",
            trigger: "body",
            run: function () {
                const pos = window.posmodel;
                pos.currentOrder.lines[0].price_unit = 0.1;
                pos.currentOrder.lines[0].product_id.lst_price = 0.1;
                pos.currentOrder.ammountTotal = 0.1;
            },
        },
        Utils.clickBtn("Pay"),
        Utils.checkIsNoBtn("Order Now"),
        ConfirmationPage.isShown(),
        ConfirmationPage.checkFinalPrice("$ 5.06"),
        Utils.clickBtn("Close"),
    ],
});

registry.category("web_tour.tours").add("self_order_create_price_on_backend_combo_correct", {
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        ProductPage.clickProduct("Office Combo"),
        ...ProductPage.setupCombo([
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
        ]),
        Utils.clickBtn("Order"),
        ...CartPage.checkCombo("Office Combo", [
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
        ]),
        Utils.clickBtn("Pay"),
        ConfirmationPage.isShown(),
        ConfirmationPage.checkFinalPrice("$ 47.56"),
        Utils.clickBtn("Ok"),
        Utils.checkIsNoBtn("Order Now"),
    ],
});

registry.category("web_tour.tours").add("self_order_create_price_on_backend_combo_modified", {
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        ProductPage.clickProduct("Office Combo"),
        ...ProductPage.setupCombo([
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
        ]),
        Utils.clickBtn("Order"),
        ...CartPage.checkCombo("Office Combo", [
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
        ]),
        {
            content: "Modify the price with javascript",
            trigger: "body",
            run: function () {
                const pos = window.posmodel;
                pos.currentOrder.lines[0].price_unit = 0.1;
                pos.currentOrder.lines[1].price_unit = 0.1;
                pos.currentOrder.lines[2].price_unit = 0.1;
                pos.currentOrder.ammountTotal = 0.1;
            },
        },
        Utils.clickBtn("Pay"),
        ConfirmationPage.isShown(),
        ConfirmationPage.checkFinalPrice("$ 47.56"),
        Utils.clickBtn("Ok"),
        Utils.checkIsNoBtn("Order Now"),
    ],
});

registry.category("web_tour.tours").add("self_order_pos_closed", {
    steps: () => [
        LandingPage.isClosed(),
        // Normal product
        Utils.clickBtn("Order Now"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.checkIsNoBtn("Order"),
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
