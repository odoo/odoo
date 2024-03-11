/** @odoo-module **/

import tour from 'web_tour.tour';
import wTourUtils from 'website.tour_utils';

tour.register('website_sale_cart_popover_tour', {
        test: true,
        url: '/shop',
    },
    [
        {
            content: "Search for the product",
            trigger: 'form input[name="search"]',
            run: 'text website_sale_cart_popover_tour_product'
        },
        wTourUtils.clickOnElement('Search', 'form:has(input[name="search"]) .oe_search_button'),
        wTourUtils.clickOnElement('website_sale_cart_popover_tour_product', 'a:contains(website_sale_cart_popover_tour_product)'),
        wTourUtils.clickOnElement('Add to Cart', '#product_detail form[action^="/shop/cart/update"] #add_to_cart'),
        {
            content: "hover on cart popover",
            trigger: '#top_menu a[href$="/shop/cart"]',
            run: () => {
                $('#top_menu a[href$="/shop/cart"]').mouseenter();
            },
        },
        {
            content: "check that popover is visible",
            trigger: '.mycart-popover:visible',
            run: () => {},
        },
        // Trigger mouseleave to close the popover
        {
            content: "hover on cart popover",
            trigger: '#top_menu a[href$="/shop/cart"]',
            run: () => {
                $('#top_menu a[href$="/shop/cart"]').mouseleave();
            },
        },
        // Check that popover is not visible
        {
            content: "check that popover is not visible",
            trigger: ':not(.mycart-popover:visible)',
            run: () => {},
        },
    ]
);
