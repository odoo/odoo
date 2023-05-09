/** @odoo-module **/

import { registry } from "@web/core/registry";
import { clickOn, clickOnBackButton, clickOnProductCard, addProductsToCart } from "./tour_utils";

registry.category("web_tour.tours").add("self_order_tour", {
    test: true,
    steps: [
        ...clickOn("My Orders", { isCheck: true, isNot: true }),
        ...clickOn("View Menu"),
        // We should now be on the product list screen
        ...addProductsToCart([1, 2]),
        // this will allow us to test if the merging of orderlines works
        ...addProductsToCart([1]),
        ...clickOn("Review"),

        // check that the products are in the card
        ...[1, 2].map((id) => clickOnProductCard(id, { isCheck: true })).flat(),

        ...clickOnProductCard(1, { isCheck: true, qty: 2 }),

        ...clickOn("Order"),
        // We should now be on the landing page screen ( because ordering redirects to the landing page )
        ...clickOn("My Orders"),
        {
            content: "Check if the status of the first order is `Draft`",
            trigger: "span.badge:contains('draft')",
            isCheck: true,
        },
        ...[1, 2].map((id) => clickOnProductCard(id, { isCheck: true })).flat(),

        ...clickOnProductCard(1, { isCheck: true, qty: 2 }),

        ...clickOnBackButton(),
        // We should now be on the Landing Page

        // We will now repeat the same steps as above, ordering again.
        // The idea is to test that the previous order is not present in the cart
        // and that the previous order is present in the `My Orders` screen
        // along with the new order.

        ...clickOn("View Menu"),
        // We should now be on the product list screen
        ...addProductsToCart([3, 4]),
        ...clickOn("Review"),
        // We should now be on the cart screen
        ...[1, 2].map((id) => clickOnProductCard(id, { isCheck: true, isNot: true })).flat(),
        ...[3, 3].map((id) => clickOnProductCard(id, { isCheck: true })).flat(),

        ...clickOn("Order"),
        // We should now be on the landing page screen
        ...clickOn("My Orders"),
        // We should now be on the orders screen

        ...[1, 2, 3, 4].map((id) => clickOnProductCard(id, { isCheck: true })).flat(),

        // {
        //     content: "Test that the 1st item is in the 1st order",
        //     // TODO: add trigger
        //     isCheck: true,
        // },
        // {
        //     content: "Test that the 2nd item is in the 1st order",
        //     // TODO: add trigger
        //     isCheck: true,
        // },
        // {
        //     content: "Test that the 3rd item is in the 2nd order",
        //     // TODO: add trigger
        //     isCheck: true,
        // },
        // {
        //     content: "Test that the 4th item is in the 2nd order",
        //     // TODO: add trigger
        //     isCheck: true,
        // },
    ],
});
