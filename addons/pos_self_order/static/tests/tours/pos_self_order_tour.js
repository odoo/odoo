/** @odoo-module **/

import { registry } from "@web/core/registry";
import { clickOn, clickOnBackButton, testProductCard, addProductsToCart } from "./tour_utils";

// TODO: use custom class names for the selectors instead of bootstrap classes
// registry.category("web_tour.tours").add("pos_self_order_pay_after_each_tour", {
//     test: true,
//     steps: [
//         // {
//         //     content: "Test that the `My Orders` button is not present",
//         //     trigger: "body:not(:has(a:contains('No products found')))",
//         //     isCheck: true,
//         // },
//         ...clickOn("View Menu"),
//         // We should now be on the product list screen
//         ...addProductsToCart([1, 2]),
//         // this will allow us to test if the merging of orderlines works
//         ...addProductsToCart([1]),
//         ...clickOn("Review"),
//         // check that the products are in the card
//         ...[1, 2].map((id) => testProductCard(id)).flat(),
//         {
//             content: "Check that Product 1 is present twice in the cart",
//             trigger:
//                 ".o_self_order_item_card:has(p:contains('2 x ').o_self_order_item_card:contains('Product 1'))",
//             isCheck: true,
//         },
//         ...clickOn("Order"),
//         // We should now be on the landing page screen ( because ordering redirects to the landing page )
//         ...clickOn("My Orders"),
//         {
//             content: "Check if the status of the first order is `Draft`",
//             trigger: ".badge:contains('draft')",
//             isCheck: true,
//         },
//         {
//             content: "Test that the first item is in the order",
//             trigger:
//                 ".o_self_order_item_card:has(p:contains('2 x ').o_self_order_item_card:contains('Product 1'))",
//             isCheck: true,
//         },
//         ...testProductCard(2),
//         ...clickOnBackButton(),
//         // We should now be on the Landing Page

//         // We will now repeat the same steps as above, ordering again.
//         // The idea is to test that the previous order is not present in the cart
//         // and that the previous order is present in the `My Orders` screen
//         // along with the new order.

//         ...clickOn("View Menu"),
//         // We should now be on the product list screen
//         ...addProductsToCart([3, 4]),
//         ...clickOn("Review"),
//         // We should now be on the cart screen
//         [1, 2].map((id) => ({
//             content: `Test that Product ${id} is not in the cart`,
//             trigger: `body:not(:has(p:contains('Product ${id}')))`,
//             isCheck: true,
//         })),

//         ...clickOn("Order"),
//         // We should now be on the landing page screen
//         ...clickOn("My Orders"),
//         // We should now be on the orders screen
//         {
//             content: "Test that the 1st item is in the 1st order",
//             // TODO: add trigger
//             isCheck: true,
//         },
//         {
//             content: "Test that the 2nd item is in the 1st order",
//             // TODO: add trigger
//             isCheck: true,
//         },
//         {
//             content: "Test that the 3rd item is in the 2nd order",
//             // TODO: add trigger
//             isCheck: true,
//         },
//         {
//             content: "Test that the 4th item is in the 2nd order",
//             // TODO: add trigger
//             isCheck: true,
//         },
//     ],
// });
