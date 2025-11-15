/** @odoo-module **/

import { registry } from "@web/core/registry";
import tourUtils from "@website_sale/js/tours/tour_utils";
import wTourUtils from "@website/js/tours/tour_utils";

registry.category("web_tour.tours").add("test_website_sale_availability_kit", {
    test: true,
    url: "/shop",
    steps: () => [
        ...tourUtils.addToCart({ productName: "Consumable Component" }),
        ...tourUtils.addToCart({ productName: "Component A" }),
        { trigger: ".availability_messages:contains(99)", isCheck: true },
        ...tourUtils.searchProduct("Super Kit Product"),
        wTourUtils.clickOnElement("Super Kit Product", `a:contains('Super Kit Product')`),
        { trigger: ".availability_messages:contains(19)", isCheck: true }, // 20 - 1 (Comp A)
        wTourUtils.clickOnElement("Add to cart", "#add_to_cart"),
        { trigger: ".availability_messages:contains(18)", isCheck: true }, // 20 - 1 (Comp A) - 1 (in cart)
        ...tourUtils.searchProduct("Kit Product"),
        wTourUtils.clickOnElement("Kit Product", `a:contains('Kit Product')`),
        { trigger: ".availability_messages:contains(19)", isCheck: true }, // 20 - 1 (Super Kit)
        wTourUtils.clickOnElement("Add to cart", "#add_to_cart"),
        { trigger: ".availability_messages:contains(18)", isCheck: true }, // 20 - 1 (Super Kit) - 1 (in cart)
        ...tourUtils.addToCart({ productName: "Component A" }),
        { trigger: ".availability_messages:contains(92)", isCheck: true },
        ...tourUtils.searchProduct("Component B"),
        wTourUtils.clickOnElement("Component B", `a:contains('Component B')`),
        wTourUtils.clickOnElement("Add to cart", "#add_to_cart"),
        { trigger: ".availability_messages:contains(89)", isCheck: true },
        ...tourUtils.searchProduct("Super Kit Product"),
        wTourUtils.clickOnElement("Super Kit Product", `a:contains('Super Kit Product')`),
        { trigger: ".availability_messages:contains(17)", isCheck: true }, // 20 - 1 (Comp A and Kit) - 1 (Comp B) - 1 (in cart)
    ],
});
