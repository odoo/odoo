odoo.define('website_sale.google_analytics', function (require) {
'use strict';

const tour = require("web_tour.tour");
const websiteSaleTracking = require('website_sale.tracking');

let itemId;

websiteSaleTracking.include({
    // Purposely don't call super to avoid call to third party (GA) during tests
    _onViewItem(event, data) {
        $('body').attr('view-event-id', data.item_id);
    },
    _onAddToCart(event, data) {
        $('body').attr('cart-event-id', data.item_id);
    },
});

tour.register('google_analytics_view_item', {
    test: true,
    url: '/shop?search=Colored T-Shirt',
},
[
    {
        content: "select Colored T-Shirt",
        trigger: '.oe_product_cart a:contains("Colored T-Shirt")',
    },
    {
        content: "wait until `_getCombinationInfo()` rpc is done",
        trigger: 'body[view-event-id]',
        timeout: 25000,
        run: () => {
            const $body = $('body');
            itemId = $body.attr('view-event-id');
            $body.removeAttr('view-event-id');
        }
    },
    {
        content: 'select another variant',
        extra_trigger: 'body:not([view-event-id])',
        trigger: 'ul.js_add_cart_variants ul.list-inline li:has(label.active) + li:has(label) input',
    },
    {
        content: 'wait until `_getCombinationInfo()` rpc is done (2)',
        // a new view event should have been generated, for another variant
        trigger: `body[view-event-id][view-event-id!=${itemId}]`,
        timeout: 25000,
        run: () => {}, // it's a check
    },
]);

tour.register('google_analytics_add_to_cart', {
    test: true,
    url: '/shop?search=Basic Shirt',
},
[
    {
        content: "select Basic Shirt",
        trigger: '.oe_product_cart a:contains("Basic Shirt")',
    },
    {
        content: "click add to cart button on product page",
        trigger: '#add_to_cart',
    },
    {
        content: 'check add to cart event',
        extra_trigger: 'body[cart-event-id]',
        trigger: 'a:has(.my_cart_quantity:containsExact(1))',
        timeout: 25000,
        run: () => {}, // it's a check
    },
]);

});
