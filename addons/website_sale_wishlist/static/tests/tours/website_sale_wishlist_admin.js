/** @odoo-module **/

import {
    clickOnEditAndWaitEditMode,
    clickOnSave,
    registerWebsitePreviewTour,
} from '@website/js/tours/tour_utils';

registerWebsitePreviewTour('shop_wishlist_admin', {
    url: '/shop?search=Rock',
},
    () => [
        {
            content: "Go to Rock shop page",
            trigger: ':iframe a:contains("Rock"):first',
            run: "click",
        },
        {
            trigger: ":iframe #product_details",
        },
        {
            content: "check list view of variants is disabled initially (when on /product page)",
            trigger: ':iframe body:not(:has(.js_product_change))',
            run: "click",
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
            content: "click on 'List View of Variants'",
            trigger: 'we-button[data-name="variants_products_list_opt"]',
            run: "click",
        },
        ...clickOnSave(),
        {
            content: "check page loaded after list of variant customization enabled",
            trigger: ':iframe .js_product_change',
            run: "click",
        },
        {
            content: "Add red product in wishlist",
            trigger: ":iframe #product_detail .o_add_wishlist_dyn:not(.disabled)",
            run: "click",
        },
        {
            content: "Check that wishlist contains 1 items",
            trigger: ':iframe .my_wish_quantity:contains(1)',
            run() {
                window.location.href = '/@/shop/wishlist';
            }
        },
        {
            content: "Check wishlist contains first variant",
            trigger: ':iframe #o_comparelist_table tr:contains("red")',
            run() {
                window.location.href = '/@/shop?search=Rock';
            }
        },
        {
            content: "Go to Rock shop page",
            trigger: ':iframe a:contains("Rock"):first',
            run: "click",
        },
        {
            content: "Switch to black Rock",
            trigger: ':iframe .js_product span:contains("black")',
            run: "click",
        },
        {
            content: "Add black rock to wishlist",
            trigger: ":iframe #product_detail .o_add_wishlist_dyn:not(.disabled)",
            run: "click",
        },
        {
            content: "Check that black product was added",
            trigger: ':iframe .my_wish_quantity:contains(2)',
            run() {
                window.location.href = '/@/shop/wishlist';
            }
        },
        {
            trigger: ':iframe #o_comparelist_table tr:contains("red")',
        },
        {
            content: "Check wishlist contains both variants",
            trigger: ':iframe #o_comparelist_table tr:contains("black")',
        },
    ]
);
