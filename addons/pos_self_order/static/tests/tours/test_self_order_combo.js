/** @odoo-module **/

import { registry } from "@web/core/registry";
import * as Utils from "../helpers/utils";
import * as CartPage from "../helpers/cart_page";
import * as ProductPage from "../helpers/product_page";

registry.category("web_tour.tours").add("self_combo_selector", {
    test: true,
    steps: () => [
        Utils.clickBtn("Order Now"),
        ProductPage.clickProduct("Office combo"),
        ...ProductPage.setupCombo([
            {
                product: "Desk Organizer",
                attributes: [
                    { name: "Size", value: "M" },
                    { name: "Fabric", value: "Leather" },
                ],
            },
            {
                product: "Desk Combination",
                attributes: [],
            },
            {
                product: "Office Chair Black",
                attributes: [],
            },
        ]),
        Utils.clickBtn("Order"),
        ...CartPage.checkCombo("Office combo", [
            {
                product: "Desk Organizer",
                attributes: [
                    { name: "Size", value: "M" },
                    { name: "Fabric", value: "Leather" },
                ],
            },
            {
                product: "Desk Combination",
                attributes: [],
            },
            {
                product: "Office Chair Black",
                attributes: [],
            },
        ]),
        Utils.clickBtn("Pay"),
        Utils.clickBtn("Ok"),
        Utils.checkIsNoBtn("Order Now"),
    ],
});
