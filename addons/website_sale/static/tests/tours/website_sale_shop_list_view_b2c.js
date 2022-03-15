/** @odoo-module **/

import tour from 'web_tour.tour';
import tourUtils from 'website_sale.tour_utils';

tour.register('shop_list_view_b2c', {
    test: true,
    url: '/shop?search=Test Product',
},
    [
        {
            content: "check price on /shop",
            trigger: '.oe_product_cart .oe_currency_value:contains("825.00")',
            run: () => {}, // It's a check.
        },
        {
            content: "select product",
            trigger: '.oe_product_cart a:contains("Test Product")',
        },
        {
            content: "check products list is disabled initially (when on /product page)",
            trigger: 'body:not(:has(.js_product_change))',
            extra_trigger: '#product_details',
            run: () => {}, // It's a check.
        },
        {
            content: "go to edit mode",
            trigger: 'a.o_frontend_to_backend_edit_btn',
        },
        {
            content: "open customize tab",
            extra_trigger: '#oe_snippets.o_loaded',
            trigger: '.o_we_customize_snippet_btn',
        },
        {
            content: "open 'Variants' selector",
            extra_trigger: '#oe_snippets .o_we_customize_panel',
            trigger: '[data-name="variants_opt"] we-toggler',
        },
        {
            content: "click on 'Products List' of the 'Variants' selector",
            trigger: 'we-button[data-name="variants_products_list_opt"]',
        },
        {
            content: "check that the iframe is reloading",
            trigger: '.o_loading_dummy',
            run: () => {}, // It's a check.
        },
        {
            content: "click on save button after the reload",
            trigger: 'div:not(.o_loading_dummy) > #oe_snippets button[data-action="save"]',
            run: 'click',
        },
        {
            content: "wait to exit edit mode",
            trigger: '.o_website_editor:not(.editor_has_snippets)',
        },
        {
            content: "check page loaded after 'Products List' enabled",
            trigger: 'iframe .js_product_change',
            run: () => {}, // It's a check.
        },
        {
            context: "check variant price",
            trigger: 'iframe .custom-radio:contains("Aluminium") .badge:contains("+") .oe_currency_value:contains("55.44")',
            run: () => {}, // It's a check.
        },
        {
            content: "check price is 825",
            trigger: 'iframe .product_price .oe_price .oe_currency_value:containsExact(825.00)',
            run: () => {}, // It's a check.
        },
        {
            content: "switch to another variant",
            trigger: 'iframe .js_product label:contains("Aluminium")',
        },
        {
            content: "verify that price has changed when changing variant",
            trigger: 'iframe .product_price .oe_price .oe_currency_value:containsExact(880.44)',
            run: () => {}, // It's a check.
        },
        {
            content: "click on 'Add to Cart' button",
            trigger: 'iframe a:contains(ADD TO CART)',
        },
        tourUtils.goToCart({backend: true}),
        {
            content: "check price on /cart",
            trigger: 'iframe #cart_products .oe_currency_value:containsExact(880.44)',
            run: () => {}, // It's a check.
        },
    ],
);
