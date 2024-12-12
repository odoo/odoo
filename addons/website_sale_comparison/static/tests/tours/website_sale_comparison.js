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
        trigger: '.o_product_circle:contains(1)',
    },
    {
        content: "check popover is closed when only one product",
        trigger: 'body:not(:has(.comparator-popover))',
    },
    {
        content: "add second product 'Color Pants' in a comparison list",
        trigger: '.oe_product_cart:contains("Color Pants")',
        run: "hover && click .oe_product_cart:contains(Color Pants) .o_add_compare",
    },
    {
        trigger: ".comparator-popover",
    },
    {
        content: "check popover is now open and compare button contains two products",
        trigger: ' .o_product_circle:contains(2)',
    },
    {
        content: "check products name are correct in the comparelist",
        trigger: '.o_product_row:contains("Color T-Shirt")',
    },
    {
        content: "check products name are correct in the comparelist",
        trigger: '.o_product_row:contains("Color Pants")',
    },
    // test form product page
    {
        content: "go to product page of Color Shoes (with variants)",
        trigger: '.oe_product_cart a:contains("Color Shoes")',
        run: "click",
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
        trigger: '.o_product_row:contains("Color Shoes (Red)")',
    },
    {
        content: "select 2nd variant(Pink Color)",
        trigger: '.variant_attribute[data-attribute_name="Color"] input[data-value_name="Pink"]:not(:visible)',
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
        trigger: '.o_product_row:contains("Color Shoes (Red)"):not(:visible)',
    },
    {
        content: "check limit is not reached",
        trigger: ':not(.o_comparelist_limit_warning)',
    },
    {
        content: "select 3nd variant(Custom)",
        trigger: '.variant_attribute[data-attribute_name="Color"] input[data-value_name="Blue"]:not(:visible)',
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
        trigger: '.o_product_comparison_table:contains("Color Pants (Red)")',
    },
    {
        content: "check 2nd product contains correct variant",
        trigger: '.o_product_comparison_table:contains("Color Shoes (Pink)")',
    },
    {
        content: "check 3rd product is correctly added",
        trigger: '.o_product_comparison_table:contains("Color Shoes (Red)")',
    },
    {
        content: "check 4th product is correctly added",
        trigger: '.o_product_comparison_table:contains("Color T-Shirt")',
    },
    {
        content: "remove Color Shoes (Pink) from compare table",
        trigger: '#o_comparelist_table .o_comparelist_remove:eq(2)',
        run: "click",
    },
    {
        content: "check color shoes with pink variant is removed",
        trigger: '#o_comparelist_table:not(:contains("Color Shoes (Pink)"))',
    },
    {
        trigger: 'body:has(.o_product_row:contains("Color T-Shirt") .o_remove)',
    },
    {
        content: "open compare menu",
        trigger: '.o_product_panel_header',
        run: "click",
    },
    {
        content: "remove product",
        trigger: '.o_product_row:contains("Color T-Shirt") .o_remove',
        run: "click",
    },
    {
        content: "click on compare button to reload",
        trigger: '.o_comparelist_button a',
        run: "click",
    },
    {
        content: "check product 'Color T-Shirt' is removed",
        trigger: '#o_comparelist_table:not(:contains("Color T-Shirt"))',
    },
    {
        content: "add product 'Color Pants' to cart",
        trigger: '.product_summary:contains("Color Pants") .a-submit:contains("Add to Cart")',
        run: "click",
    },
        clickOnElement('Continue Shopping', 'button:contains("Continue Shopping")'),
        tourUtils.goToCart(),
    {
        content: "check product correctly added to cart",
        trigger: '#cart_products:contains("Color Pants") .js_quantity[value="1"]',
    },
    ]});
