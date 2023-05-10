/** @odoo-module **/

import { registry } from "@web/core/registry";
import { clickOn } from "./tour_utils";

registry.category("web_tour.tours").add("pos_qr_menu_tour", {
    test: true,
    steps: [
        {
            content: "Check that the `Pos is Closed` notification is present",
            trigger: ".o_notification_content:contains(restaurant is closed)",
            isCheck: true,
        },
        ...clickOn("My Orders", { isCheck: true, isNot: true }),
        ...clickOn("View Menu"),
        {
            content: "Test that products are present",
            trigger: ".o_self_order_item_card",
            isCheck: true,
        },
        ...clickOn("Add to Cart", { isCheck: true, isNot: true }),

        {
            content: "Test that the 'No products found' message is not present",
            trigger: "body:not(:has(p:contains('No products found')))",
            isCheck: true,
        },
        // We should be on the products screen now
        {
            content: "Test that the tag list is present",
            trigger: ".o_self_order_searchbar_filter li",
            isCheck: true,
        },
        {
            content: "Test that the first tag is active",
            trigger: ".o_self_order_searchbar_filter li:nth-child(1) span.active",
            isCheck: true,
        },
        {
            content: "Test that the search icon is present",
            trigger: ".oi.oi-search",
        },
        {
            content: "Test that the search icon is not present after clicking on it",
            trigger: "body:not(:has(.oi.oi-search))",
            isCheck: true,
        },
        {
            content: "Test that the tag list is not present after clicking on the search icon",
            trigger: "body:not(:has(.o_search_bar_filter li))",
            isCheck: true,
        },
        {
            content: "Test that the search box is visible after clicking on the search icon",
            trigger: "input[placeholder='Pizza']",
            run: "text Desk",
        },
        {
            content: "Test that the search results are present",
            trigger: ".o_self_order_item_card",
            isCheck: true,
        },
        {
            content: "Test that the 'No products found' message is not present",
            trigger: "body:not(:has(p:contains('No products found')))",
            isCheck: true,
        },
        {
            trigger: "input",
            run: "text xyzxyzxyzxyxyxyxyxyxzxyxyxyxyxyxyxyxyyxzyxzyxzyxyzxyzyx",
        },
        {
            content: "Test that no products are present",
            trigger: "body:not(:has(.o_self_order_item_card))",
            isCheck: true,
        },
        {
            content: "Test that the 'No products found' message is present",
            trigger: "p:contains('No products found')",
            isCheck: true,
        },
        {
            content: "Test that the button to exit the search box is present and click on it",
            trigger: ".fa.fa-times",
        },
        {
            content: "Test that the search icon is present again",
            trigger: ".oi.oi-search",
            isCheck: true,
        },
        {
            content: "Test that the tag list is present and click on the 2nd tag",
            trigger: ".o_self_order_searchbar_filter li:nth-child(2)",
        },
        {
            content: "Test that the tag is highlighted and click on it to deactivate it",
            trigger: ".o_self_order_searchbar_filter li:nth-child(2) span.active",
        },
        {
            content: "Test that the tag is not highlighted anymore",
            trigger: ".o_self_order_searchbar_filter li:nth-child(2)",
            isCheck: true,
        },
        // After clicking on the 2nd tag, it will be deactivated and the screen should scroll up to the top
        // when we reach the top of the screen, the intersection observer shoould trigger and select the 1st tag
        // we check that the 1st tag is now active <-- this would mean that the intersection observer is working properly
        {
            content: "Test that the first tag is active",
            trigger: ".o_self_order_searchbar_filter li:nth-child(1) span.active",
            isCheck: true,
        },
        {
            content: "Test that the product description is present and click on it",
            trigger: "p.o_self_order_item_card_description",
        },
        // We should now be on the product screen
        {
            content: "Test that the product name is present in the product screen",
            trigger: ".o_self_order_product_main_view_name",
            isCheck: true,
        },
        ...clickOn("Add", { isCheck: true, isNot: true }),
        {
            content: "Test that the back button is present on the product screen and click on it",
            trigger: "nav.o_self_order_navbar > button",
        },
        // now that we are back on the product list screen, we click the back button again to go to the landing page
        {
            content:
                "Test that the back button is present on the product list screen and click on it",
            trigger: "nav.o_self_order_navbar > button",
        },
        // on the landing page, we look for the View Menu button
        // finding it also means that the back button works properly
        ...clickOn("View Menu", { isCheck: true }),
        {
            content: "Test that the back button is not present on the landing page",
            trigger: "body:not(:has(nav.o_self_order_navbar > button))",
            isCheck: true,
        },
    ],
});
