import { registry } from "@web/core/registry";
import * as Utils from "@pos_self_order/../tests/tours/utils/common";
import * as CartPage from "@pos_self_order/../tests/tours/utils/cart_page_util";
import * as ProductPage from "@pos_self_order/../tests/tours/utils/product_page_util";
import * as ConfirmationPage from "@pos_self_order/../tests/tours/utils/confirmation_page_util";
import * as LandingPage from "@pos_self_order/../tests/tours/utils/landing_page_util";
import * as Numpad from "@point_of_sale/../tests/generic_helpers/numpad_util";

registry.category("web_tour.tours").add("self_combo_selector", {
    steps: () => [
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
        ]),
        Utils.clickBtn("Next"),
        ...ProductPage.setupCombo([
            {
                product: "Combo Product 5",
                attributes: [],
            },
            {
                product: "Combo Product 8",
                attributes: [],
            },
        ]),
        Utils.clickBtn("Add to cart"),
        Utils.clickBtn("Checkout"),
        {
            trigger: ".btn .oi-plus",
            run: "click",
        },
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
        Utils.clickBtn("Order"),
        ConfirmationPage.orderNumberShown(),
        ConfirmationPage.orderNumberIs("S", "1"),
        Utils.clickBtn("Ok"),
        Utils.checkIsNoBtn("Order Now"),
    ],
});

registry.category("web_tour.tours").add("self_combo_selector_category", {
    steps: () => [
        Utils.clickBtn("Order Now"),
        ProductPage.clickProduct("Test Combo"),
        ...ProductPage.setupCombo([
            {
                product: "Combo Product 5",
                attributes: [],
            },
        ]),
        Utils.clickBtn("Add to cart"),
        Utils.clickBtn("Checkout"),
        Utils.clickBtn("Order"),
        Utils.clickBtn("Ok"),
        Utils.checkIsNoBtn("Order Now"),
    ],
});

registry.category("web_tour.tours").add("test_product_dont_display_all_variants", {
    steps: () => [
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Test-In"),
        ProductPage.clickCategory("Uncategorised"),
        ProductPage.clickProduct("Meal Combo"),
        ProductPage.clickComboProduct("Coke always never"),
        Utils.clickBtn("Red"),
        Utils.clickBtn("Next"),
        Utils.clickBtn("Add to cart"),
        ProductPage.clickProduct("Meal Combo"),
        ProductPage.clickComboProduct("Coke always only"),
        Utils.clickBtn("Add to cart"),
        ProductPage.clickProduct("Meal Combo"),
        ProductPage.clickComboProduct("Coke never only"),
        Utils.clickBtn("Red"),
        Utils.clickBtn("Add to cart"),
    ],
});

registry.category("web_tour.tours").add("test_self_order_combo_multiple_qty", {
    steps: () => [
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Test-In"),
        ProductPage.clickCategory("Uncategorised"),
        ProductPage.clickProduct("Combo Drinks"),
        ...ProductPage.setupCombo([
            {
                product: "Water",
                attributes: [],
            },
        ]),
        Utils.clickBtn("Add to cart"),
        Utils.clickBtn("Checkout"),
        {
            trigger: ".btn .oi-plus",
            run: "click",
        },
        Utils.clickBtn("Order"),
        Numpad.click("2"),
        Utils.clickBtn("Order"),
        Utils.clickBtn("Close"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Test-In"),
        ProductPage.clickCategory("Uncategorised"),
        ProductPage.clickProduct("Price for drinks"),
        ...ProductPage.setupCombo([
            {
                product: "Water 2",
                attributes: [],
            },
        ]),
        Utils.clickBtn("Add to cart"),
        Utils.clickBtn("Checkout"),
        {
            trigger: ".btn .oi-plus",
            run: "click",
        },
        {
            trigger: ".btn .oi-plus",
            run: "click",
        },
        Utils.clickBtn("Order"),
        Numpad.click("3"),
        Utils.clickBtn("Order"),
    ],
});
