/** @odoo-module **/

import { registry } from "@web/core/registry";
import tourUtils from "@website_sale/js/tours/tour_utils";

registry.category("web_tour.tours").add('shop_buy_product', {
    test: true,
    url: '/shop',
    steps: () => [
        ...tourUtils.searchProduct("conference chair"),
        {
            content: "select conference chair",
            trigger: '.oe_product_cart:first a:contains("Conference Chair")',
        },
        {
            content: "select Conference Chair Aluminium",
            extra_trigger: '#product_detail',
            trigger: 'label:contains(Aluminium) input',
        },
        {
            content: "select Conference Chair Steel",
            extra_trigger: '#product_detail',
            trigger: 'label:contains(Steel) input',
        },
        {
            id: 'add_cart_step',
            content: "click on add to cart",
            extra_trigger: 'label:contains(Steel) input:propChecked',
            trigger: '#product_detail form[action^="/shop/cart/update"] #add_to_cart',
        },
            tourUtils.goToCart(),
        {
            content: "add suggested",
            extra_trigger: '#wrap:not(:has(#cart_products:contains("Storage Box")))',
            trigger: '.oe_cart:has(tr:contains("Storage Box")) a:contains("Add to Cart")',
        },
        {
            content: "add one more",
            extra_trigger: '#cart_products tr:contains("Storage Box")',
            trigger: '#cart_products tr:contains("Steel") a.js_add_cart_json:eq(1)',
        },
        {
            content: "remove Storage Box",
            extra_trigger: '#cart_products tr:contains("Steel") input.js_quantity:propValue(2)',
            trigger: '#cart_products tr:contains("Storage Box") a.js_add_cart_json:first',
        },
        {
            content: "set one",
            extra_trigger: '#wrap:not(:has(#cart_products tr:contains("Storage Box")))',
            trigger: '#cart_products input.js_quantity',
            run: 'text 1',
        },
        {
            content: "go to checkout",
            extra_trigger: '#cart_products input.js_quantity:propValue(1)',
            trigger: 'a[href*="/shop/checkout"]',
        },
        ...tourUtils.payWithTransfer(true),
    ]
});
