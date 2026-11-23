/** @odoo-module **/

import { registry } from "@web/core/registry";
import * as Utils from "../helpers/utils";
import * as CartPage from "../helpers/cart_page";
import * as ProductPage from "../helpers/product_page";

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
