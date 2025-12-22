/** @odoo-module **/

import {registry} from '@web/core/registry';
import * as tourUtils from '@website_sale/js/tours/tour_utils';

registry.category('web_tour.tours').add('shop_update_cart', {
    url: '/shop',
    steps: () => [
        ...tourUtils.searchProduct("conference chair", { select: true }),
        {
            trigger: "#product_detail",
        },
        {
            content: "select Conference Chair Aluminium",
            trigger: 'label:contains(Aluminium) input',
            run: "click",
        },
        {
            trigger: "#product_detail",
        },
        {
            content: "select Conference Chair Steel",
            trigger: 'label:contains(Steel) input',
            run: "click",
        },
        {
            trigger: "label:contains(Steel) input:checked",
        },
        {
            content: "click on add to cart",
            trigger: '#product_detail form[action^="/shop/cart/update"] #add_to_cart',
            run: "click",
        },
        {
            content: "click in modal on 'Proceed to checkout' button",
            trigger: 'button:contains("Proceed to Checkout")',
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "add suggested",
            trigger: '.js_cart_lines:has(a:contains("Storage Box")) a:contains("Add to cart")',
            run: "click",
        },
        {
            trigger: '#cart_products div>a>h6:contains("Storage Box")',
        },
        {
            content: "add one more",
            trigger: '#cart_products div:has(div>a>h6:contains("Steel")) a.js_add_cart_json:eq(1)',
            run: "click",
        },
        {
            trigger:
                '#cart_products div:has(div>a>h6:contains("Steel")) input.js_quantity:value(2)',
        },
        {
            content: "remove Storage Box",
            trigger:
                '#cart_products div:has(div>a>h6:contains("Storage Box")) a.js_add_cart_json:first',
            run: "click",
        },
        {
            trigger: '#wrap:not(:has(#cart_products div>a>h6:contains("Storage Box")))',
        },
        {
            content: "set one",
            trigger: '#cart_products input.js_quantity',
            run: "edit 1",
        },
    ],
});
