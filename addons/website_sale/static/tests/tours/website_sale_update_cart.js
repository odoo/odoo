import { registry } from '@web/core/registry';
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
            trigger: '#product_detail form #add_to_cart',
            run: "click",
        },
        {
            content: "click in modal on 'Proceed to checkout' button",
            trigger: 'button:contains("Checkout")',
            run: "click",
            expectUnloadPage: true,
        },
        ...tourUtils.assertCartContains({productName: 'Conference Chair', combinationName: 'Steel'}),
        {
            content: "add suggested",
            trigger: '.js_cart_lines:has(a:contains("Storage Box")) button:contains("Add to cart")',
            run: "click",
            expectUnloadPage: true,
        },
        {
            trigger: '#cart_products a[name="o_cart_line_product_link"]>h6:contains("Storage Box")',
        },
        {
            content: "remove Storage Box",
            trigger: '#cart_products div:has(a[name="o_cart_line_product_link"]>h6:contains("Storage Box")) a:has(i.oi-minus)',
            run: "click",
        },
        {
            trigger: '#wrap:not(:has(#cart_products a[name="o_cart_line_product_link"]>h6:contains("Storage Box")))',
        },
        {
            content: "add one more",
            trigger: '#cart_products div:has(a[name="o_cart_line_product_link"]>h6:contains("Conference Chair")) a:has(i.oi-plus)',
            run: "click",
        },
        {
            trigger: '#cart_products div:has(div>a>h6:contains("Conference Chair")) input.js_quantity:value(2)',
        },
        {
            content: "set one",
            trigger: '#cart_products input.js_quantity',
            run: "edit 1",
        },
    ],
});
