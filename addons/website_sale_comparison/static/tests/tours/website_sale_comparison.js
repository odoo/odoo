/** @odoo-module **/

    import { registry } from "@web/core/registry";
    import * as tourUtils from "@website_sale/js/tours/tour_utils";

    registry.category("web_tour.tours").add('product_comparison', {
        url: "/shop",
        steps: () => [
    // test from shop page
    {
        content: "add first product 'Warranty' in a comparison list",
        trigger: '.oe_product_cart:contains("Warranty") .o_add_compare',
        run: "click",
    },
    {
        content: "check compare button contains one product",
        trigger: '.o_product_circle:contains(1)',
    },
    {
        content: "check popover is closed when only one product",
        trigger: 'body:not(:has(.comparator-popover))',
    },
    {
        content: "add second product 'Conference Chair' in a comparison list",
        trigger: '.oe_product_cart:contains("Conference Chair") .o_add_compare',
        run: "click",
    },
    {
        trigger: ".comparator-popover",
    },
    {
        content: "check popover is now open and compare button contains two products",
        trigger: ' .o_product_circle:contains(2)',
    },
    {
        trigger: '.o_product_row:contains("Warranty")',
    },
    {
        content: "check products name are correct in the comparelist",
        trigger: '.o_product_row:contains("Conference Chair")',
    },
    // test form product page
    {
        content: "go to product page of customizable desk(with variants)",
        trigger: '.oe_product_cart a:contains("Customizable Desk")',
        run: "click",
    },
    {
        trigger: "#product_details",
    },
    {
        content: "check compare button is still there and contains 2 products",
        trigger: '.o_product_circle:contains(2)',
    },
    {
        content: "check popover is closed after changing page",
        trigger: 'body:not(:has(.comparator-popover))',
    },
    {
        content: "add first variant to comparelist",
        trigger: '.o_add_compare_dyn',
        run: "click",
    },
    {
        trigger: ".comparator-popover",
    },
    {
        content: "check the comparelist is now open and contains 3rd product with correct variant",
        trigger: '.o_product_row:contains("Customizable Desk (Steel, White)")',
    },
    {
        content: "select 2nd variant(Black Color)",
        trigger: '.variant_attribute[data-attribute_name="Color"] input[data-value_name="Black"]',
        run: function (actions) {
          document.querySelector('img[class*="product_detail_img"]').setAttribute('data-image-to-change', 1);
          actions.click();
        },
    },
    {
        trigger: 'img[class*="product_detail_img"]:not([data-image-to-change])',
    },
    {
        content: "click on compare button to add in comparison list when variant changed",
        trigger: '.o_add_compare_dyn',
        run: "click",
    },
    {
        trigger: '.o_product_circle:contains(4)',
    },
    {
        content: "comparelist contains 4th product with correct variant",
        trigger: '.o_product_row:contains("Customizable Desk (Steel, Black)"):not(:visible)',
    },
    {
        content: "check limit is not reached",
        trigger: ':not(.o_comparelist_limit_warning)',
    },
    {
        content: "select 3nd variant(Custom)",
        trigger: '.variant_attribute[data-attribute_name="Legs"] input[data-value_name="Custom"]',
        run: "click",
    },
    {
        trigger: 'body:not(:has(.carousel-indicators))', // there is 1 image on the custom variant
    },
    {
        content: "click on compare button to add in comparison list when variant changed",
        trigger: '.o_add_compare_dyn',
        run: "click",
    },
    {
        content: "check limit is reached",
        trigger: '.o_comparelist_limit_warning',
    },
    {
        content: "click on compare button",
        trigger: '.o_comparelist_button a',
        run: "click",
    },
    // test on compare page
    {
        content: "check 1st product contains correct variant",
        trigger: '.o_product_comparison_table:contains("Conference Chair (Steel)")',
    },
    {
        content: "check 2nd product contains correct variant",
        trigger: '.o_product_comparison_table:contains("Customizable Desk (Steel, White)")',
    },
    {
        content: "check 3rd product is correctly added",
        trigger: '.o_product_comparison_table:contains("Customizable Desk (Steel, Black)")',
    },
    {
        content: "check 4th product is correctly added",
        trigger: '.o_product_comparison_table:contains("Warranty")',
    },
    {
        content: "remove Customizable Desk (Steel, Black) from compare table",
        trigger: '#o_comparelist_table .o_comparelist_remove:eq(2)',
        run: "click",
    },
    {
        content: "check customizable table with black variant is removed",
        trigger: '#o_comparelist_table:not(:contains("Customizable Desk (Steel, Black)"))',
    },
    {
        trigger: 'body:has(.o_product_row:contains("Warranty") .o_remove)',
    },
    {
        content: "open compare menu",
        trigger: '.o_product_panel_header',
        run: "click",
    },
    {
        content: "remove product",
        trigger: '.o_product_row:contains("Warranty") .o_remove',
        run: "click",
    },
    {
        content: "click on compare button to reload",
        trigger: '.o_comparelist_button a',
        run: "click",
    },
    {
        content: "check product 'Warranty' is removed",
        trigger: '#o_comparelist_table:not(:contains("Warranty"))',
    },
    {
        content: "add product 'Conference Chair' to cart",
        trigger: '.product_summary:contains("Conference Chair") .a-submit:contains("Add to Cart")',
        run: "click",
    },
        tourUtils.goToCart(),
    {
        content: "check product correctly added to cart",
        trigger: '#cart_products:contains("Conference Chair") .js_quantity[value="1"]',
    },
    ]});
