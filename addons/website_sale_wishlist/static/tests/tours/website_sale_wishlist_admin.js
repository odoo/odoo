odoo.define('website_sale_wishlist_admin.tour', function (require) {
'use strict';

const wTourUtils = require("website.tour_utils");

wTourUtils.registerWebsitePreviewTour('shop_wishlist_admin', {
    url: '/shop?search=Rock',
    test: true,
},
    [
        {
            content: "Go to Rock shop page",
            trigger: 'iframe a:contains("Rock"):first',
        },
        {
            content: "check list view of variants is disabled initially (when on /product page)",
            trigger: 'iframe body:not(:has(.js_product_change))',
            extra_trigger: 'iframe #product_details',
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
            content: "click on 'List View of Variants'",
            trigger: 'we-button[data-name="variants_products_list_opt"]',
        },
        ...wTourUtils.clickOnSave(),
        {
            content: "check page loaded after list of variant customization enabled",
            trigger: 'iframe .js_product_change',
        },
        {
            content: "Add red product in wishlist",
            trigger: 'iframe #product_detail .o_add_wishlist_dyn:not(".disabled")',
        },
        {
            content: "Check that wishlist contains 1 items",
            trigger: 'iframe .my_wish_quantity:contains(1)',
            run: function () {
                window.location.href = '/@/shop/wishlist';
            }
        },
        {
            content: "Check wishlist contains first variant",
            trigger: 'iframe #o_comparelist_table tr:contains("red")',
            run: function () {
                window.location.href = '/@/shop?search=Rock';
            }
        },
        {
            content: "Go to Rock shop page",
            trigger: 'iframe a:contains("Rock"):first',
        },
        {
            content: "Switch to black Rock",
            trigger: 'iframe .js_product span:contains("black")',
        },
        {
            content: "Add black rock to wishlist",
            trigger: 'iframe #product_detail .o_add_wishlist_dyn:not(".disabled")',
        },
        {
            content: "Check that black product was added",
            trigger: 'iframe .my_wish_quantity:contains(2)',
            run: function () {
                window.location.href = '/@/shop/wishlist';
            }
        },
        {
            content: "Check wishlist contains both variants",
            extra_trigger: 'iframe #o_comparelist_table tr:contains("red")',
            trigger: 'iframe #o_comparelist_table tr:contains("black")',
            run: function () {}, // This is a check
        },
    ]
);

});
