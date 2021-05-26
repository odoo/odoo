odoo.define('website_sale_loyalty.tour_shop_cart_reward', function (require) {
'use strict';

const tour = require('web_tour.tour');
require('web.dom_ready');

tour.register('shop_cart_reward', {
    test: true,
    url: '/shop?search=Office Lamp',
},
[
    {
        content: "select Office Lamp",
        trigger: '.oe_product a:containsExact("Office Lamp")',
    },
    {
        content: "click add to cart",
        trigger: '#product_details #add_to_cart',
    },
    {
        content: "go to cart",
        trigger: 'a:has(.my_cart_quantity:containsExact(1))',
    },
    {
        content: "check product is in cart",
        trigger: 'td.td-product_name:contains("Office Lamp")',
    },
    {
        content: "check won points",
        trigger: 'div#cart_total tr:has(td:contains("Won")) td:has(span:containsExact("400.0"))',
    },
    {
        content: "check total points",
        trigger: 'div#cart_total tr:has(td:contains("Total")) td:has(span:containsExact("650.0"))',
    },
    {
        content: "add pen",
        trigger: 'table#rewards_catalog a[data-reward-id="1"]',
    },
    {
        content: "check spent points",
        trigger: 'div#cart_total tr:has(td:contains("Spent")) td:has(span:containsExact("5.0"))',
    },
    {
        content: "one more reward",
        trigger: 'table#cart_products tr:contains("Simple Pen") td.td-qty input',
        run: "text 2",
    },
    {
        content: "check spent points again",
        trigger: 'div#cart_total tr:has(td:contains("Spent")) td:has(span:containsExact("10.0"))',
    },
    {
        content: "other rewards available are still available",
        trigger: 'body:has(table#rewards_catalog)',
    },
    {
        content: "many more rewards => no more rewards available",
        trigger: 'table#cart_products tr:contains("Simple Pen") td.td-qty input',
        run: "text 40",
    },
    {
        content: "check spent points again again",
        trigger: 'div#cart_total tr:has(td:contains("Spent")) td:has(span:containsExact("200.0"))',
    },
    {
        content: "check no more rewards available",
        trigger: 'body:not(:has(table#rewards_catalog))',
    },
    {
        content: "but checkout is still available",
        trigger: 'body:has(a:has(span:containsExact("Process Checkout")))',
    },
    {
        content: "too many rewards => no more rewards available",
        trigger: 'table#cart_products tr:contains("Simple Pen") td.td-qty input',
        run: "text 100",
    },
    {
        content: "check spent points again again again",
        trigger: 'div#cart_total tr:has(td:contains("Spent")) td:has(span:containsExact("500.0"))',
    },
    {
        content: "checkout becomes unavailable",
        trigger: 'body:not(:has(a:has(span:containsExact("Process Checkout"))))',
    },
    {
        content: "revert to 2 rewards",
        trigger: 'table#cart_products tr:contains("Simple Pen") td.td-qty input',
        run: "text 2",
    },
    {
        content: "rewards catalog returns",
        trigger: 'body:has(table#rewards_catalog)',
    },
    {
        content: "checkout",
        trigger: 'a:has(span:containsExact("Process Checkout"))',
    },
    {
        content: "Select `Wire Transfer` payment method",
        trigger: '#payment_method label:contains("Wire Transfer")',
    },
    {
        content: "Pay Now",
        extra_trigger: '#payment_method label:contains("Wire Transfer") input:checked,#payment_method:not(:has("input:radio:visible"))',
        trigger: 'button[name="o_payment_submit_button"]:visible:not(:disabled)',
    },
    {
        content: "wait until done",
        trigger: 'div.oe_cart:has(strong:contains("Payment Information"))',
    },
]);
});
