/** @odoo-module **/

import tour from 'web_tour.tour';
import tourUtils from 'website_sale.tour_utils';

tour.register('shop_customize', {
    test: true,
    url: '/shop?enable_editor=1',
},
    [
        {
            content: "open customize tab",
            extra_trigger: '#oe_snippets.o_loaded',
            trigger: '.o_we_customize_snippet_btn',
        },
        {
            content: "click on 'Attributes'",
            extra_trigger: '#oe_snippets .o_we_customize_panel',
            trigger: 'we-button[data-name="attributes_opt"]',
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
            content: "select product attribute Steel",
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
            content: "wait the product page to be loaded",
            trigger: 'iframe #product_detail',
            run: function () {},
        },
        {
            content: "check list view of variants is disabled initially",
            trigger: 'iframe body:not(:has(.js_product_change))',
            run: function () {},
        },
        {
            content: "enter edit mode",
            trigger: '.o_edit_website_container > a',
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
            context: "check variant price",
            trigger: 'iframe .custom-radio:contains("Aluminium") .badge:contains("+") .oe_currency_value:contains("50.4")',
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
        {
            content: "enter edit mode",
            trigger: '.o_edit_website_container > a',
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
            content: "click on 'Options' of the 'Variants' selector",
            trigger: 'we-button[data-name="variants_options_opt"]',
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
            content: "check page loaded after list of variant customization disabled",
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
        {
            content: "enter edit mode",
            trigger: '.o_edit_website_container > a',
        },
        {
            content: "open customize tab",
            extra_trigger: '#oe_snippets.o_loaded',
            trigger: '.o_we_customize_snippet_btn',
        },
        {
            content: "remove 'Attributes'",
            extra_trigger: '#oe_snippets .o_we_customize_panel',
            trigger: 'we-button[data-name="attributes_opt"]',
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
            content: "finish",
            extra_trigger: 'iframe body:not(:has(#products_grid_before .js_attributes))',
            trigger: 'iframe #wrap:not(:has(li:has(.my_cart_quantity):visible))',
            run: function () {}, // it's a check
        },
    ],
);
