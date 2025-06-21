/** @odoo-module **/

import { registry } from "@web/core/registry";
import * as Utils from "../helpers/utils";
import * as LandingPage from "../helpers/landing_page";
import * as ProductPage from "../helpers/product_page";

registry.category("web_tour.tours").add("self_order_is_close", {
    test: true,
    steps: () => [
        LandingPage.isClosed(),
        Utils.clickBtn("Order Now"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.checkIsNoBtn("Order"),
    ],
});

registry.category("web_tour.tours").add("self_order_is_open_consultation", {
    test: true,
    steps: () => [
        LandingPage.isOpened(),
        Utils.clickBtn("Order Now"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.checkIsNoBtn("Order"),
    ],
});

registry.category("web_tour.tours").add("self_order_pos_is_closed", {
    test: true,
    steps: () => [
        LandingPage.isClosed(),
        // Normal product
        Utils.clickBtn("Order Now"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.checkIsNoBtn("Order"),
        // Product with attributes
        ProductPage.clickProduct("Desk Organizer"),
        ...ProductPage.setupAttribute([
            { name: "Size", value: "M" },
            { name: "Fabric", value: "Leather" },
        ], false),
        Utils.checkIsNoBtn("Add to cart"),
        Utils.clickBtn("Discard"),
        // Combo product
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
        ], false),
        Utils.checkIsNoBtn("Add to cart"),
    ],
});
