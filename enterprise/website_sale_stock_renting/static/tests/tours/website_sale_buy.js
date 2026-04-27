/** @odoo-module **/

import { registry } from "@web/core/registry";
import * as tourUtils from '@website_sale/js/tours/tour_utils';

registry.category("web_tour.tours").add('shop_buy_rental_stock_product', {
    url: '/shop',
    steps: () => [
        ...tourUtils.searchProduct("computer", { select: true }),
        {
            content: "Check if the default data is in the date picker input",
            trigger: '.o_daterange_picker[data-has-default-dates=true]',
        },
        {
            content: "Open daterangepicker",
            trigger: 'input[name=renting_start_date]',
            run: "click",
        },
        { // Select the first day of the next month, this ensures that the daterange is always valid.
            content:  "Select Date field",
            trigger:  ".o_date_picker:nth-child(2) > .o_date_item_cell:not(.o_out_of_range)",
            run: "click",
        },
        {
            content: "Pick start time",
            trigger: '.o_time_picker_select:eq(0)',
            run: "select 8",
        },
        {
            content: "Pick end time",
            trigger: '.o_time_picker_select:eq(2)',
            run: "select 12",
        },
        {
            content: "Apply change",
            trigger: '.o_datetime_buttons button.o_apply',
            run: "click",
        },
        {
            content: "Add one quantity",
            trigger: '.css_quantity a.js_add_cart_json i.fa-plus',
            run: "click",
        },
        {
            content: "click on add to cart",
            trigger: '#product_detail form[action^="/shop/cart/update"] #add_to_cart',
            run: "click",
        },
        tourUtils.goToCart({quantity: 2}),
        {
            content: "Verify there is a Computer",
            trigger: '#cart_products div a h6:contains("Computer")',
        },
        {
            content: "Verify there are 2 quantity of Computers",
            trigger: '#cart_products div div.css_quantity input[value="2"]',
        },
        {
            content: "Go back on the Computer",
            trigger: '#cart_products div>a>h6:contains("Computer")',
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "Verify there is a warning message",
            trigger: 'div#threshold_message_renting:contains("Only 3 Units still available during the selected period.")',
        },
        tourUtils.goToCart({quantity: 2}),
        {
            content: "Check quantity",
            trigger: '#cart_products input.js_quantity:value(2)',
        },
        {
            content: "Check amount",
            trigger: '#cart_products .oe_currency_value:contains(28.00)',
        },
        tourUtils.goToCheckout(),
        tourUtils.confirmOrder(),
        ...tourUtils.payWithTransfer({ redirect: true }),
    ]
});


registry.category("web_tour.tours").add("website_availability_update", {
    url: "/shop",
    steps: () => [
        ...tourUtils.searchProduct("Test Product with Variants", { select: true }),
        {
            trigger:
                '#threshold_message_renting:contains("Only 1 Units still available during the selected period.")',
        },
        {
            trigger: '.o_wsale_product_attribute li:eq(1) input[type="radio"]',
            run: "click",
        },
        {
            trigger: 'span[name="renting_warning_message"]',
        },
    ],
});

registry.category("web_tour.tours").add("test_website_availability_while_continuing_selling", {
    url: "/shop",
    steps: () => [
        ...tourUtils.searchProduct("Computer", { select: true }),
        {
            trigger:
                "#threshold_message_renting:contains('Only 2 Units still available during the selected period.')",
        },
        {
            trigger: ".o_website_sale_daterange_picker_input",
            run: "click",
        },
        {
            trigger: ".o_date_item_cell:contains(22)",
            run: "click",
        },
        {
            trigger: ".o_date_item_cell:contains(24)",
            run: "click",
        },
        {
            trigger: ".o_apply:contains(Apply)",
            run: "click",
        },
        {
            trigger:
                "#threshold_message_renting:contains('Only 5 Units still available during the selected period.')",
            run: () => {},
        },
    ],
});
