/** @odoo-module **/

import { registry } from "@web/core/registry";
import tourUtils from '@website_sale/js/tours/tour_utils';

registry.category("web_tour.tours").add('shop_buy_rental_stock_product', {
    test: true,
    url: '/shop',
    steps: () => [
        {
            content: "Search computer write text",
            trigger: 'form input[name="search"]',
            run: "text computer",
        },
        {
            content: "Search computer click",
            trigger: 'form:has(input[name="search"]) .oe_search_button',
        },
        {
            content: "Select computer",
            trigger: '.oe_product_cart:first a:contains("Computer")',
        },
        {
            content: "Check if the default data is in the date picker input",
            trigger: '.o_daterange_picker[data-has-default-dates=true]',
            run: function () {}, // it's a check
        },
        {
            content: "Open daterangepicker",
            trigger: 'input[name=renting_start_date]',
            run: "click",
        },
        { // ensures only one day is selected
            content:  "Select Date field",
            trigger:  ".o_date_picker .o_highlight_end",
            run: "click",
        },
        {
            content: "Pick start time",
            trigger: '.o_time_picker_select:nth(0)',
            run: "text 8",
        },
        {
            content: "Pick end time",
            trigger: '.o_time_picker_select:nth(2)',
            run: "text 12",
        },
        {
            content: "Apply change",
            trigger: '.o_datetime_buttons button.o_apply',
        },
        {
            content: "Add one quantity",
            trigger: '.css_quantity a.js_add_cart_json i.fa-plus',
        },
        {
            content: "click on add to cart",
            trigger: '#product_detail form[action^="/shop/cart/update"] #add_to_cart',
        },
        tourUtils.goToCart({quantity: 2}),
        {
            content: "Verify there is a Computer",
            trigger: '#cart_products div a h6:contains("Computer")',
            isCheck: true,
        },
        {
            content: "Verify there are 2 quantity of Computers",
            trigger: '#cart_products div div.css_quantity input[value=2]',
            isCheck: true,
        },
        {
            content: "Go back on the Computer",
            trigger: '#cart_products div>a>h6:contains("Computer")',
        },
        {
            content: "Verify there is a warning message",
            trigger: 'div#threshold_message_renting:contains("Only 3 Units still available during the selected period.")',
            run: function () {}, // it's a check
        },
        tourUtils.goToCart({quantity: 2}),
        {
            content: "Check quantity",
            trigger: '#cart_products input.js_quantity:propValue(2)',
            run: function () {}, // it's a check,
        },
        {
            content: "Check amount",
            trigger: '#cart_products .oe_currency_value:contains(28.00)',
            run: function () {}, // it's a check,
        },
        tourUtils.goToCheckout(),
        ...tourUtils.payWithTransfer(true),
    ]
});
