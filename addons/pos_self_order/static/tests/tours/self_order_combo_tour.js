import { registry } from "@web/core/registry";
import * as Utils from "@pos_self_order/../tests/tours/utils/common";
import * as CartPage from "@pos_self_order/../tests/tours/utils/cart_page_util";
import * as ProductPage from "@pos_self_order/../tests/tours/utils/product_page_util";

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
        {
            trigger: '.btn:contains("＋")',
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
        Utils.clickBtn("Pay"),
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
        Utils.clickBtn("Order"),
        Utils.clickBtn("Pay"),
        Utils.clickBtn("Ok"),
        Utils.checkIsNoBtn("Order Now"),
    ],
});
