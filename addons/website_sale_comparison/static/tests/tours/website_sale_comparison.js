import { registry } from "@web/core/registry";
import { clickOnElement } from '@website/js/tours/tour_utils';
import * as tourUtils from "@website_sale/js/tours/tour_utils";

    registry.category("web_tour.tours").add('product_comparison', {
        url: "/shop",
        steps: () => [
    // test from shop page
    {
        content: "add first product 'Color T-Shirt' in a comparison list",
        trigger: '.oe_product_cart:contains("Color T-Shirt")',
        run: "hover && click .oe_product_cart:contains(Color T-Shirt) .o_add_compare",
    },
    {
        content: "check compare button contains one product",
        trigger: '.o_wsale_comparison_bottom_bar .badge:contains(1)',
    },
    {
        content: "add second product 'Color Pants' in a comparison list",
        trigger: '.oe_product_cart:contains("Color Pants")',
        run: "hover && click .oe_product_cart:contains(Color Pants) .o_add_compare",
    },
    {
        content: "check that the compare button contains two products",
        trigger: '.o_wsale_comparison_bottom_bar .badge:contains(2)',
    },
    {
        content: "check products name are correct in the comparelist",
        trigger: '[name="product_comparison_bottom_bar_row"]:contains("Color T-Shirt")',
    },
    {
        content: "check products name are correct in the comparelist",
        trigger: '[name="product_comparison_bottom_bar_row"]:contains("Color Pants")',
    },
    {
        content: "remove product",
        trigger: '[name="product_comparison_bottom_bar_row"]:contains("Color T-Shirt") button:has(i.oi-close)',
        run: "click",
    },
    {
        content: "wait for 'Color T-Shirt' to be removed from the popover",
        trigger: '[name="product_comparison_bottom_bar_row"]:not(:contains("Color T-Shirt"))',
    },
    {
        content: "re-add 'Color T-Shirt' in comparison list",
        trigger: '.oe_product_cart:contains("Color T-Shirt")',
        run: "hover && click .oe_product_cart:contains(Color T-Shirt) .o_add_compare",
    },
    // test form product page
    {
        content: "go to product page of Color Shoes (with variants)",
        trigger: '.oe_product_cart a:contains("Color Shoes")',
        run: "click",
        expectUnloadPage: true,
    },
    {
        content: "check compare button is still there and contains 2 products",
        trigger: '.o_wsale_comparison_bottom_bar .badge:contains(2)',
    },
    {
        content: "add first variant to comparelist",
        trigger: '.o_add_compare_dyn',
        run: "click",
    },
    {
        content: "check the comparelist is now open and contains 3rd product with correct variant",
        trigger: '[name="product_comparison_bottom_bar_row"]:contains("Color Shoes (Red)")',
    },
    {
        content: "select 2nd variant(Pink Color)",
        trigger: '.variant_attribute[data-attribute-name="Color"] input[data-value-name="Pink"]:not(:visible)',
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
        content: "comparelist contains 4th product with correct variant",
        trigger: '[name="product_comparison_bottom_bar_row"]:contains("Color Shoes (Red)")',
    },
    {
        content: "check limit is not reached",
        trigger: ':not(.o_notification:contains("You can compare up to 4 products at a time."))',
    },
    {
        content: "select 3nd variant(Custom)",
        trigger: '.variant_attribute[data-attribute-name="Color"] input[data-value-name="Blue"]:not(:visible)',
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
        trigger: '.o_notification:contains("You can compare up to 4 products at a time.")',
    },
    {
        content: "click on compare button",
        trigger: 'a:contains("Compare")',
        run: "click",
        expectUnloadPage: true,
    },
    // test on compare page
    {
        content: "check 1st product contains correct variant",
        trigger: '.product_summary a:contains("Color Pants (Red)")',
    },
    {
        content: "check 2nd product contains correct variant",
        trigger: '.product_summary a:contains("Color Shoes (Pink)")',
    },
    {
        content: "check 3rd product is correctly added",
        trigger: '.product_summary a:contains("Color Shoes (Red)")',
    },
    {
        content: "check 4th product is correctly added",
        trigger: '.product_summary a:contains("Color T-Shirt")',
    },
    {
        content: "remove Color Shoes (Pink) from compare table",
        trigger: '#o_comparelist_table .o_comparelist_remove:eq(2)',
        run: "click",
        expectUnloadPage: true,
    },
    {
        content: "check color shoes with pink variant is removed",
        trigger: '#o_comparelist_table:not(:contains("Color Shoes (Pink)"))',
    },
    {
        content: "add product 'Color Pants' to cart",
        trigger: '.product_summary:contains("Color Pants") button:contains("Add to Cart")',
        run: "click",
    },
        clickOnElement('Add to cart', 'button[name="website_sale_product_configurator_continue_button"]'),
        tourUtils.goToCart(),
    {
        content: "check product correctly added to cart",
        trigger: '#cart_products:contains("Color Pants") .js_quantity[value="1"]',
    },
    ]});
