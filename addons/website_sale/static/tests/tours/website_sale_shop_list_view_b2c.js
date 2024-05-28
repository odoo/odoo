/** @odoo-module **/

import tourUtils from '@website_sale/js/tours/tour_utils';
import wTourUtils from '@website/js/tours/tour_utils';
import { stepUtils } from "@web_tour/tour_service/tour_utils";

wTourUtils.registerWebsitePreviewTour('shop_list_view_b2c', {
    test: true,
    url: '/shop?search=Test Product',
},
    () => [
        stepUtils.waitIframeIsReady(),
        {
            content: "check price on /shop",
            trigger: ':iframe .oe_product_cart .oe_currency_value:contains("825.00")',
            run: () => {}, // It's a check.
        },
        {
            content: "select product",
            trigger: ':iframe .oe_product_cart a:contains("Test Product")',
            run: "click",
        },
        {
            content: "check products list is disabled initially (when on /product page)",
            trigger: ':iframe body:not(:has(.js_product_change))',
            extra_trigger: ':iframe #product_details',
            run: () => {}, // It's a check.
        },
        ...wTourUtils.clickOnEditAndWaitEditMode(),
        {
            content: "open customize tab",
            trigger: '.o_we_customize_snippet_btn',
            run: "click",
        },
        {
            content: "open 'Variants' selector",
            extra_trigger: '#oe_snippets .o_we_customize_panel',
            trigger: '[data-name="variants_opt"] we-toggler',
            run: "click",
        },
        {
            content: "click on 'Products List' of the 'Variants' selector",
            trigger: 'we-button[data-name="variants_products_list_opt"]',
            run: "click",
        },
        ...wTourUtils.clickOnSave(),
        {
            content: "check page loaded after 'Products List' enabled",
            trigger: ':iframe .js_product_change',
            run: () => {}, // It's a check.
        },
        {
            context: "check variant price",
            trigger: ':iframe .form-check:contains("Aluminium") .badge:contains("+") .oe_currency_value:contains("55.44")',
            run: () => {}, // It's a check.
        },
        {
            content: "check price is 825",
            trigger: ":iframe .product_price .oe_price .oe_currency_value:contains(/^825.00$/)",
            run: () => {}, // It's a check.
        },
        {
            content: "switch to another variant",
            trigger: ':iframe .js_product label:contains("Aluminium")',
            run: "click",
        },
        {
            content: "verify that price has changed when changing variant",
            trigger: ":iframe .product_price .oe_price .oe_currency_value:contains(/^880.44$/)",
            run: () => {}, // It's a check.
        },
        {
            content: "click on 'Add to Cart' button",
            trigger: ':iframe a:contains(Add to cart)',
            run: "click",
        },
        tourUtils.goToCart({backend: true}),
        {
            content: "check price on /cart",
            trigger: ":iframe #cart_products .oe_currency_value:contains(/^880.44$/)",
            run: () => {}, // It's a check.
        },
    ],
);
