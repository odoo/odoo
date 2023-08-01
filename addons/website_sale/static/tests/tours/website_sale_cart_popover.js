/** @odoo-module **/

import { registry } from "@web/core/registry";
import wsTourUtils from '@website_sale/js/tours/tour_utils';

registry.category("web_tour.tours").add('website_sale_cart_popover_tour', {
    test: true,
    url: '/shop',
    steps: () => [
        ...wsTourUtils.addToCart({productName: "website_sale_cart_popover_tour_product"}),
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
});
