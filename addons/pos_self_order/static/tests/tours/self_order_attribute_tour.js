/** @odoo-module **/

import { registry } from "@web/core/registry";
import * as Utils from "@pos_self_order/../tests/tours/utils/common";
import * as CartPage from "@pos_self_order/../tests/tours/utils/cart_page_util";
import * as ProductPage from "@pos_self_order/../tests/tours/utils/product_page_util";

registry.category("web_tour.tours").add("self_attribute_selector", {
    test: true,
    steps: () => [
        Utils.clickBtn("Order Now"),
        ProductPage.clickProduct("Desk Organizer"),
        ...ProductPage.setupAttribute([
            { name: "Size", value: "M" },
            { name: "Fabric", value: "Leather" },
        ]),
        Utils.clickBtn("Order"),
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
        Utils.clickBtn("Order"),
        CartPage.checkAttribute("Desk Organizer", [
            { name: "Size", value: "L" },
            { name: "Fabric", value: "Leather" },
        ]),
        CartPage.checkProduct("Desk Organizer", "8.17", "1"),
        Utils.clickBtn("Pay"),
        Utils.clickBtn("Ok"),
        Utils.clickBtn("My Order"),
        Utils.clickBtn("Pay"),
        Utils.clickBtn("Ok"),
        Utils.checkIsNoBtn("Order Now"),
    ],
});
