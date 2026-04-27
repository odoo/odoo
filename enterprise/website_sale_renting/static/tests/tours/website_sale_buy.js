/** @odoo-module **/

import { registry } from "@web/core/registry";
import * as tourUtils from '@website_sale/js/tours/tour_utils';

registry.category("web_tour.tours").add('shop_buy_rental_product', {
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
        tourUtils.goToCheckout(),
        tourUtils.confirmOrder(),
        {
            content: "verify checkout page",
            trigger: 'span div.o_wizard_step_active:contains("Payment")',
        },
    ]
});
