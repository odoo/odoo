/** @odoo-module **/

import { goToCart } from '@website_sale/js/tours/tour_utils';
import {
    clickOnEditAndWaitEditMode,
    clickOnSave,
    registerWebsitePreviewTour,
} from '@website/js/tours/tour_utils';
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registerWebsitePreviewTour('shop_list_view_b2c', {
    url: '/shop?search=Test Product',
},
    () => [
        stepUtils.waitIframeIsReady(),
        {
            content: "check price on /shop",
            trigger: ':iframe .oe_product_cart .oe_currency_value:contains("825.00")',
        },
        {
            content: "select product",
            trigger: ':iframe .oe_product_cart a:contains("Test Product")',
            run: "click",
        },
        {
            trigger: ":iframe #product_details",
        },
        {
            content: "check products list is disabled initially (when on /product page)",
            trigger: ':iframe body:not(:has(.js_product_change))',
        },
        ...clickOnEditAndWaitEditMode(),
        {
            content: "open customize tab",
            trigger: '.o_we_customize_snippet_btn',
            run: "click",
        },
        {
            trigger: "#oe_snippets .o_we_customize_panel",
        },
        {
            content: "open 'Variants' selector",
            trigger: '[data-name="variants_opt"] we-toggler',
            run: "click",
        },
        {
            content: "click on 'Products List' of the 'Variants' selector",
            trigger: 'we-button[data-name="variants_products_list_opt"]',
            run: "click",
        },
        ...clickOnSave(),
        {
            content: "check page loaded after 'Products List' enabled",
            trigger: ':iframe .js_product_change',
        },
        {
            content: "check variant price",
            trigger: ':iframe .form-check:contains("Aluminium") .badge:contains("+") .oe_currency_value:contains("55.44")',
        },
        {
            content: "check price is 825",
            trigger: ":iframe .product_price .oe_price .oe_currency_value:contains(/^825.00$/)",
        },
        {
            content: "switch to another variant",
            trigger: ':iframe .js_product label:contains("Aluminium")',
            run: "click",
        },
        {
            content: "verify that price has changed when changing variant",
            trigger: ":iframe .product_price .oe_price .oe_currency_value:contains(/^880.44$/)",
        },
        {
            content: "click on 'Add to Cart' button",
            trigger: ':iframe a:contains(Add to cart)',
            run: "click",
        },
        goToCart({ backend: true, expectUnloadPage: false }),
        {
            content: "check price on /cart",
            trigger: ":iframe #cart_products .oe_currency_value:contains(/^880.44$/)",
        },
    ],
);
