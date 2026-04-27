/** @odoo-module **/

import { registry } from "@web/core/registry";
import { delay } from "@odoo/hoot-dom";
import * as tourUtils from '@website_sale/js/tours/tour_utils';


function getFutureDate(days) {
    days = (days ?? 0) + 7;
    return luxon.DateTime.now().set({ weekday: 1 }).plus({ days }).toFormat('MM/dd/yyyy');
}

registry.category("web_tour.tours").add("rental_cart_update_duration", {
    url: "/shop",
    steps: () => [
        ...tourUtils.searchProduct("computer", { select: true }),
        {
            content: "Wait computer informations are loaded",
            trigger: "img.product_detail_img[src*='Computer']",
        },
        {
            content: "Open daterangepicker",
            trigger: "input[name=renting_start_date]",
            run: "click",
        },
        {
            content: "Wait for the datepicker to be opened",
            trigger: ".o_time_picker_select",
        },
        {
            content: "Pick start time",
            trigger: ".o_time_picker_select:eq(0)",
            run: "select 6",
        },
        {
            content: "Pick start time",
            trigger: ".o_time_picker_select:eq(1)",
            run: "select 0",
        },
        {
            content: "Pick end time",
            trigger: ".o_time_picker_select:eq(2)",
            run: "select 12",
        },
        {
            content: "Pick end time",
            trigger: ".o_time_picker_select:eq(3)",
            run: "select 0",
        },
        {
            content: "Apply change",
            trigger: ".o_datetime_buttons button.o_apply",
            run: "click",
        },
        {
            content: "click on add to cart",
            trigger:
                '#product_detail form[action^="/shop/cart/update"] #add_to_cart',
            run: "click",
        },
        tourUtils.goToCart(),
        {
            content: "Verify Rental Product is in the cart",
            trigger: '#cart_products div div.css_quantity input[value="1"]',
        },
        {
            content: "Open daterangepicker",
            trigger: "input[name=renting_start_date]",
            run: "click",
        },
        {
            content: "Wait for the datepicker to be opened",
            trigger: ".o_time_picker_select",
        },
        {
            content: "Pick start time",
            trigger: ".o_time_picker_select:eq(0)",
            run: "select 8",
        },
        {
            content: "Apply change",
            trigger: ".o_datetime_buttons button.o_apply",
            run: "click",
        },
        {
            content: "Verify order line rental period start time",
            trigger: 'div.text-muted.small span:contains("08:00")',
        },
        {
            content: "Verify order line rental period return time",
            trigger: 'div.text-muted.small span:contains("12:00")',
        },
    ],
});

registry.category('web_tour.tours').add('date_based_rental_duration', {
    steps: () => [
        ...tourUtils.searchProduct("Computer"),
        {
            content: "Select computer",
            trigger: '.oe_product_cart:first a:contains(Computer)',
            run: 'click',
        },
        {
            content: "Select the return date",
            trigger: 'input[name=renting_end_date]',
            async run(helpers) {
                await delay(1000);
                await helpers.edit(getFutureDate(2));
                await helpers.press("Tab");
            },        
        },
        {
            content: "Rent for 2 days",
            trigger: 'input[name=renting_start_date]',
            async run(helpers) {
                await delay(1000);
                await helpers.edit(getFutureDate(1));
                await helpers.press("Tab");
            },
        },
        {
            content: "Add to cart",
            trigger: '#product_detail form[action^="/shop/cart/update"] #add_to_cart',
            run: 'click',
        },
        {
            content: "Rental duration should display 2 days",
            trigger: 'span.o_renting_details:contains(2 Days)',
        },
        tourUtils.goToCart(),
        {
            content: "Wait for cart to load",
            trigger: 'h3:contains("Order overview")',
        },
        ...tourUtils.assertCartAmounts({ untaxed: "40.00" }), // $ 20.00 per day
    ],
});
