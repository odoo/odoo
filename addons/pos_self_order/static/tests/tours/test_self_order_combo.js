/** @odoo-module **/

import { registry } from "@web/core/registry";
import * as Utils from "../helpers/utils";
import * as CartPage from "../helpers/cart_page";
import * as ProductPage from "../helpers/product_page";

registry.category("web_tour.tours").add("self_combo_selector", {
    test: true,
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

registry.category("web_tour.tours").add("test_self_order_combo_correct_order", {
    steps: () =>
        [
            Utils.clickBtn("Order Now"),
            ProductPage.clickProduct("Office Combo"),
            ...ProductPage.setupCombo([
                {
                    product: "Combo Product 1",
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
            ProductPage.clickProduct("Office Combo"),
            ...ProductPage.setupCombo([
                {
                    product: "Combo Product 2",
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
            Utils.clickBtn("Pay"),
            Utils.clickBtn("Ok"),
            Utils.checkIsNoBtn("Order Now"),
        ].flat(),
});
