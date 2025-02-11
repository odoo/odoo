/** @odoo-module **/

import { registry } from "@web/core/registry";
import tourUtils from "@website_sale/js/tours/tour_utils";
import { nbsp } from "@web/core/utils/strings";

registry.category("web_tour.tours").add('website_sale_cart_notification', {
    test: true,
    url: '/shop',
    steps: () => [
        ...tourUtils.addToCart({productName: 'website_sale_cart_notification_product_1'}),
        {
            content: "check that 1 website_sale_cart_notification_product_1 was added",
            trigger: '.toast-body span:contains("1 x website_sale_cart_notification_product_1")',
        },
        {
            content: "check the price of 1 website_sale_cart_notification_product_1",
            trigger: '.toast-body div:contains("$'+nbsp+'1,000.00")',
        },
        {
            content: "close the notification",
            trigger: '.toast-header button.btn-close',
        },
        {
            content: "check that the notification is closed",
            trigger: 'div.position-absolute.w-100.h-100.top-0.pe-none',
            run: () => {
                if ($('div.position-absolute.w-100.h-100.top-0.pe-none div').length !== 1) {
                    console.error('The cart notification is not closed!');
                }
            },
            isCheck: true,
        },
        ...tourUtils.searchProduct('website_sale_cart_notification_product_2'),
        {
            content: "select website_sale_cart_notification_product_2",
            trigger: '.oe_product_cart:first a:contains("website_sale_cart_notification_product_2")',
        },
        {
            content: "change quantity",
            extra_trigger: '#product_detail',
            trigger: '#product_detail form[action^="/shop/cart/update"] input[name=add_qty]',
            run: 'text 3',
        },
        {
            content: "click on add to cart",
            extra_trigger: '#product_detail',
            trigger: '#product_detail form[action^="/shop/cart/update"] #add_to_cart',
        },
        {
            content: "check that 3 website_sale_cart_notification_product_2 was added",
            trigger: '.toast-body span:contains("3 x website_sale_cart_notification_product_2")',
        },
        {
            content: "check that the novariants/custom attributes are displayed.",
            trigger: '.toast-body span.text-muted.small:contains("Size: S")',
        },
        {
            content: "check the price of 1 website_sale_cart_notification_product_2",
            trigger: '.toast-body div:contains("$'+nbsp+'15,000.00")',
        },
        {
            content: "Go To Cart",
            trigger: '.toast-body a:contains("View cart")',
        },
        tourUtils.assertCartContains({
            productName: 'website_sale_cart_notification_product_1',
            backend: false,
        }),
        tourUtils.assertCartContains({
            productName: 'website_sale_cart_notification_product_2',
            backend: false,
        }),
    ]
});
