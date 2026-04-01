import { registry } from "@web/core/registry";
import * as Utils from "@pos_self_order/../tests/tours/utils/common";
import * as CartPage from "@pos_self_order/../tests/tours/utils/cart_page_util";
import * as ProductPage from "@pos_self_order/../tests/tours/utils/product_page_util";
import * as LandingPage from "@pos_self_order/../tests/tours/utils/landing_page_util";
import { negateStep } from "@point_of_sale/../tests/generic_helpers/utils";

registry.category("web_tour.tours").add("self_attribute_selector", {
    steps: () => [
        Utils.clickBtn("Order Now"),
        ProductPage.clickProduct("Desk Organizer"),
        ...ProductPage.setupAttribute([
            { name: "Size", value: "M" },
            { name: "Fabric", value: "Leather" },
        ]),
        Utils.clickBtn("Checkout"),
        CartPage.checkAttribute("Desk Organizer", [
            { name: "Size", value: "M" },
            { name: "Fabric", value: "Leather" },
        ]),
        CartPage.checkProduct("Desk Organizer", "7.02", "1"),
        CartPage.clickBack(),
        ProductPage.clickProduct("Desk Organizer"),
        ...ProductPage.setupAttribute([
            { name: "Size", value: "L" },
            { name: "Fabric", value: "Leather" },
        ]),
        Utils.clickBtn("Checkout"),
        CartPage.checkAttribute("Desk Organizer", [
            { name: "Size", value: "L" },
            { name: "Fabric", value: "Leather" },
        ]),
        CartPage.checkProduct("Desk Organizer", "8.17", "1"),
        Utils.clickBtn("Order"),
        Utils.clickBtn("Ok"),
        Utils.clickBtn("My Order"),
        Utils.clickBtn("Order"),
        Utils.clickBtn("Ok"),
        Utils.checkIsNoBtn("Order Now"),
    ],
});

registry.category("web_tour.tours").add("self_multi_attribute_selector", {
    steps: () => [
        Utils.clickBtn("Order Now"),
        ProductPage.clickProduct("Multi Check Attribute Product"),
        ...ProductPage.setupAttribute(
            [
                { name: "Attribute 1", value: "Attribute Val 1" },
                { name: "Attribute 1", value: "Attribute Val 2" },
            ],
            false
        ),
        ProductPage.verifyIsCheckedAttribute("Attribute 1", ["Attribute Val 1", "Attribute Val 2"]),
    ],
});

registry.category("web_tour.tours").add("selfAlwaysAttributeVariants", {
    steps: () => [
        Utils.clickBtn("Order Now"),
        ProductPage.waitProduct("Chair"),
        ProductPage.clickProduct("Chair"),
        ...ProductPage.setupAttribute([{ name: "Color", value: "White" }]),
        Utils.clickBtn("Checkout"),
        CartPage.checkProduct("Chair", "10", "1"),
        CartPage.checkAttribute("Chair", [{ name: "Color", value: "White" }]),
        CartPage.clickBack(),
        ProductPage.clickProduct("Chair"),
        ...ProductPage.setupAttribute([{ name: "Color", value: "Red" }]),
        Utils.clickBtn("Checkout"),
        CartPage.checkProduct("Chair", "15", "1"),
        CartPage.checkAttribute("Chair", [{ name: "Color", value: "Red" }]),
        Utils.clickBtn("Order"),
        Utils.clickBtn("Ok"),
        Utils.clickBtn("My Order"),
        Utils.clickBtn("Order"),
        Utils.clickBtn("Ok"),
        Utils.checkIsNoBtn("Order Now"),
    ],
});

registry.category("web_tour.tours").add("self_order_product_info", {
    steps: () => [
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Test-In"),
        {
            trigger: ".o_self_product_box:contains('Product Info Test') .product_info_icon",
            run: "click",
        },
        {
            trigger: '.modal-body:contains("Nice Product")',
            run: () => {},
        },
    ],
});

registry.category("web_tour.tours").add("self_attribute_selector_shows_images", {
    steps: () => [
        Utils.clickBtn("Order Now"),
        ProductPage.clickProduct("Desk Organizer"),
        ProductPage.attributeHasColorDot("White"),
        ProductPage.attributeHasImage("Blue"),
    ],
});

registry.category("web_tour.tours").add("test_self_order_multi_check_attribute_with_extra_price", {
    steps: () =>
        [
            Utils.clickBtn("Order Now"),
            ProductPage.clickProduct("Desk Organizer"),
            {
                content: "Check required badge for Fabric attribute",
                trigger: "h2:contains('Fabric') .badge:contains('Required')",
            },
            {
                content: "Check no required badge for Add-ons attribute",
                trigger: "h2:contains('Add-ons'):not(:has(.badge))",
            },
            ProductPage.setupAttribute(
                [
                    { name: "Fabric", value: "Leather" },
                    { name: "Add-ons", value: "Pen Holder" },
                    { name: "Add-ons", value: "Mini Drawer" },
                    { name: "Colour", value: "Blue" },
                ],
                false
            ),
            Utils.checkMissingRequiredsExists(),
            Utils.clickMissingRequireds(),
            {
                content: "Size attribute selection is visible",
                trigger: "h2:contains('Size'):visible",
            },
            ProductPage.setupAttribute([{ name: "Size", value: "M" }], false),
            negateStep(Utils.checkMissingRequiredsExists()),
            Utils.clickBtn("Add to Cart"),
            Utils.clickBtn("Checkout"),
            CartPage.checkProduct("Desk Organizer", "11.62", "1"),
            Utils.clickBtn("Order"),
            Utils.clickBtn("Ok"),
            Utils.clickBtn("My Order"),
        ].flat(),
});
