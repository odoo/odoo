/** @odoo-module **/

import tourUtils from 'website_sale.tour_utils';
import wTourUtils from 'website.tour_utils';

wTourUtils.registerWebsitePreviewTour('shop_customize', {
    url: '/shop',
    edition: true,
    test: true,
},
    [
        ...wTourUtils.clickOnSave(),
        {
            content: "select product attribute Steel",
            extra_trigger: "iframe body:not(.editor_enable)",
            trigger: 'iframe form.js_attributes input:not(:checked) + label:contains(Steel - Test)',
        },
        {
            content: "check the selection",
            trigger: 'iframe form.js_attributes input:checked + label:contains(Steel - Test)',
            run: function () {}, // it's a check
        },
        {
            content: "select product",
            extra_trigger: 'iframe body:not(:has(.oe_website_sale .oe_product_cart:eq(3)))',
            trigger: 'iframe .oe_product_cart a:contains("Test Product")',
        },
        {
            content: "check list view of variants is disabled initially",
            extra_trigger: "iframe #product_detail",
            trigger: 'iframe body:not(:has(.js_product_change))',
            run: function () {},
        },
        ...wTourUtils.clickOnEditAndWaitEditMode(),
        {
            content: "open customize tab",
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
        ...wTourUtils.clickOnSave(),
        {
            context: "check variant price",
            extra_trigger: "iframe body:not(.editor_enable)",
            trigger: 'iframe .form-check:contains("Aluminium") .badge:contains("+") .oe_currency_value:contains("50.4")',
            run: function () {},
        },
        {
            content: "check price is 750",
            trigger: "iframe .product_price .oe_price .oe_currency_value:containsExact(750.00)",
            run: function () {},
        },
        {
            content: "switch to another variant",
            trigger: "iframe .js_product label:contains('Aluminium')",
        },
        {
            content: "verify that price has changed when changing variant",
            trigger: "iframe .product_price .oe_price .oe_currency_value:containsExact(800.40)",
            run: function () {},
        },
        ...wTourUtils.clickOnEditAndWaitEditMode(),
        {
            content: "open customize tab",
            trigger: '.o_we_customize_snippet_btn',
        },
        {
            content: "open 'Variants' selector",
            extra_trigger: '#oe_snippets .o_we_customize_panel',
            trigger: '[data-name="variants_opt"] we-toggler',
        },
        {
            content: "click on 'Options' of the 'Variants' selector",
            trigger: 'we-button[data-name="variants_options_opt"]',
        },
        ...wTourUtils.clickOnSave(),
        {
            content: "check page loaded after list of variant customization disabled",
            extra_trigger: "iframe body:not(.editor_enable)",
            trigger: "iframe .js_product:not(:has(.js_product_change))",
            run: function () {}, // it's a check
        },
        {
            content: "check price is 750",
            trigger: "iframe .product_price .oe_price .oe_currency_value:containsExact(750.00)",
            run: function () {},
        },
        {
            content: "switch to Aluminium variant",
            trigger: 'iframe .js_product input[data-value_name="Aluminium"]',
        },
        {
            content: "verify that price has changed when changing variant",
            trigger: "iframe .product_price .oe_price .oe_currency_value:containsExact(800.40)",
            run: function () {}, // it's a check
        },
        {
            content: "switch back to Steel variant",
            trigger: "iframe .js_product label:contains('Steel - Test')",
        },
        {
            content: "check price is 750",
            trigger: "iframe .product_price .oe_price .oe_currency_value:containsExact(750.00)",
            run: function () {},
        },
        {
            content: "click on 'Add to Cart' button",
            trigger: "iframe a:contains(ADD TO CART)",
        },
        {
            content: "check quantity",
            trigger: 'iframe .my_cart_quantity:containsExact(1),.o_extra_menu_items .fa-plus',
            run: function () {}, // it's a check
        },
        tourUtils.goToCart({backend: true}),
        {
            content: "click on shop",
            trigger: "iframe a:contains(Continue Shopping)",
            extra_trigger: 'iframe body:not(:has(#products_grid_before .js_attributes))',
        },
        ...wTourUtils.clickOnEditAndWaitEditMode(),
        {
            content: "open customize tab",
            trigger: '.o_we_customize_snippet_btn',
        },
        {
            content: "remove 'Attributes'",
            extra_trigger: '#oe_snippets .o_we_customize_panel',
            trigger: 'we-button[data-name="attributes_opt"]',
        },
        ...wTourUtils.clickOnSave(),
        {
            content: "wait to exit edit mode",
            trigger: '.o_website_preview:not(.editor_has_snippets)',
        },
        {
            content: "finish",
            extra_trigger: 'iframe body:not(:has(#products_grid_before .js_attributes))',
            trigger: 'iframe #wrap:not(:has(li:has(.my_cart_quantity):visible))',
            run: function () {}, // it's a check
        },
    ],
);
