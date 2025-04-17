import { registry } from "@web/core/registry";
import * as Utils from "@pos_self_order/../tests/tours/utils/common";
import * as CartPage from "@pos_self_order/../tests/tours/utils/cart_page_util";
import * as ProductPage from "@pos_self_order/../tests/tours/utils/product_page_util";

registry.category("web_tour.tours").add("self_attribute_selector", {
    steps: () => [
        Utils.clickBtn("Order Now"),
        ProductPage.clickProduct("Configurable Chair"),
        ...ProductPage.setupAttribute([
            { name: "Color", value: "Red" },
            { name: "Chair Legs", value: "Wood" },
            { name: "Fabrics", value: "Leather" },
        ]),
        Utils.clickBtn("Checkout"),
        CartPage.checkAttribute("Configurable Chair", [
            { name: "Color", value: "Red" },
            { name: "Chair Legs", value: "Wood" },
            { name: "Fabrics", value: "Leather" },
        ]),
        CartPage.checkProduct("Configurable Chair", "46.0", "1"),
        CartPage.clickBack(),
        ProductPage.clickProduct("Configurable Chair"),
        ...ProductPage.setupAttribute([
            { name: "Color", value: "Red" },
            { name: "Chair Legs", value: "Metal" },
            { name: "Fabrics", value: "Wool" },
        ]),
        Utils.clickBtn("Checkout"),
        CartPage.checkAttribute("Configurable Chair", [
            { name: "Color", value: "Red" },
            { name: "Chair Legs", value: "Metal" },
            { name: "Fabrics", value: "Wool" },
        ]),
        CartPage.checkProduct("Configurable Chair", "57.5", "1"),
        Utils.clickBtn("Pay"),
        Utils.clickBtn("Ok"),
        Utils.clickBtn("My Order"),
        Utils.clickBtn("Pay"),
        Utils.clickBtn("Ok"),
        Utils.checkIsNoBtn("Order Now"),
    ],
});

registry.category("web_tour.tours").add("self_multi_attribute_selector", {
    steps: () => [
        Utils.clickBtn("Order Now"),
        ProductPage.clickProduct("Desk Organizer"),
        ...ProductPage.setupAttribute(
            [
                { name: "Multi", value: "Value 1" },
                { name: "Multi", value: "Value 2" },
            ],
            false
        ),
        ProductPage.verifyIsCheckedAttribute("Multi", ["Value 1", "Value 2"]),
    ],
});

registry.category("web_tour.tours").add("selfAlwaysAttributeVariants", {
    steps: () => [
        Utils.clickBtn("Order Now"),
        ProductPage.clickProduct("Desk Organizer"),
        ...ProductPage.setupAttribute([{ name: "Color", value: "Black" }]),
        Utils.clickBtn("Checkout"),
        CartPage.checkProduct("Desk Organizer (Black)", "11.5", "1"),
        CartPage.clickBack(),
        ProductPage.clickProduct("Desk Organizer"),
        ...ProductPage.setupAttribute([{ name: "Color", value: "White" }]),
        Utils.clickBtn("Checkout"),
        CartPage.checkProduct("Desk Organizer (White)", "17.25", "1"),
        Utils.clickBtn("Pay"),
        Utils.clickBtn("Ok"),
        Utils.clickBtn("My Order"),
        Utils.clickBtn("Pay"),
        Utils.clickBtn("Ok"),
        Utils.checkIsNoBtn("Order Now"),
    ],
});

registry.category("web_tour.tours").add("self_order_product_info", {
    steps: () => [
        Utils.clickBtn("Order Now"),
        {
            trigger: ".self_order_product_card:contains('Desk Organizer') .product-information-tag",
            run: "click",
        },
        {
            trigger: '.modal-body:contains("Nice Product")',
            run: () => {},
        },
    ],
});
