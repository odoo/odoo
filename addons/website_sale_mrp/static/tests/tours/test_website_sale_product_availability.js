/** @odoo-module **/

import { registry } from "@web/core/registry";
import { clickOnElement } from "@website/js/tours/tour_utils";
import { addToCart, searchProduct } from "@website_sale/js/tours/tour_utils";

registry.category("web_tour.tours").add("test_website_sale_availability_kit", {
    url: "/shop",
    steps: () => [
        ...addToCart({ productName: "Consumable Component" }),
        ...addToCart({ productName: "Component A" }),
        { trigger: ".availability_messages:contains(99)" },
        ...searchProduct("Super Kit Product"),
        clickOnElement("Super Kit Product", `a:contains('Super Kit Product')`),
        { trigger: ".availability_messages:contains(19)" }, // 20 - 1 (Comp A)
        clickOnElement("Add to cart", "#add_to_cart"),
        { trigger: ".availability_messages:contains(18)" }, // 20 - 1 (Comp A) - 1 (in cart)
        ...searchProduct("Kit Product"),
        clickOnElement("Kit Product", `a:contains('Kit Product')`),
        { trigger: ".availability_messages:contains(19)" }, // 20 - 1 (Super Kit)
        clickOnElement("Add to cart", "#add_to_cart"),
        { trigger: ".availability_messages:contains(18)" }, // 20 - 1 (Super Kit) - 1 (in cart)
        ...addToCart({ productName: "Component A" }),
        { trigger: ".availability_messages:contains(92)" },
        ...searchProduct("Component B"),
        clickOnElement("Component B", `a:contains('Component B')`),
        clickOnElement("Add to cart", "#add_to_cart"),
        { trigger: ".availability_messages:contains(89)" },
        ...searchProduct("Super Kit Product"),
        clickOnElement("Super Kit Product", `a:contains('Super Kit Product')`),
        { trigger: ".availability_messages:contains(17)" }, // 20 - 1 (Comp A and Kit) - 1 (Comp B) - 1 (in cart)
    ],
});
