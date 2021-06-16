odoo.define('website_sale.google_analytics', function (require) {
'use strict';

const tour = require("web_tour.tour");
const websiteSaleTracking = require('website_sale.tracking');
const WebsiteSale = require('website_sale.website_sale').WebsiteSale;

let itemId;

tour.register('google_analytics_view_item', {
    test: true,
    url: '/shop?search=Customizable Desk',
},
[
    {
        content: "select customizable desk",
        trigger: '.oe_product_cart a:contains("Customizable Desk")',
    },
    {
        content: "check view_item events",
        trigger: '#product_detail',
        run: () => {
            // If we don't explicitly wait for the getCombinationInfo ajax
            // call, the tour fails when running in phantomjs. The actual
            // test is executed in a separate tour stage, triggered when
            // the ajax call is ready.
            WebsiteSale.getCombinationInfoPromise().then(() => {
                $('body').addClass('combination_info_ready');
            });
        }
    },
    {
        trigger: 'body.combination_info_ready',
        run: () => {
            const events = websiteSaleTracking.getEvents('view_item');
            $('body').removeClass('combination_info_ready');
            if (events.length !== 1) {
                console.error('No view item was generated');
            } else {
                itemId = events[0]['item_id'];
            }
        }
    },
    {
        content: 'select another variant',
        trigger: 'ul.js_add_cart_variants ul.list-inline li:has(label.active) + li:has(label) input',
    },
    {
        content: "check view_item events",
        trigger: '#product_detail',
        run: () => {
            WebsiteSale.getCombinationInfoPromise().then(() => {
                $('body').addClass('combination_info_ready');
            });
        }
    },
    {
        trigger: 'body.combination_info_ready',
        run: () => {
            const events = websiteSaleTracking.getEvents('view_item');
            $('body').removeClass('combination_info_ready');
            if (events.length !== 2) {
                console.error('No second view event was generated');
            } else if (itemId === events[1]['item_id']) {
                console.error('The second variant has the same id as the first one');
            }
        }
    },
]);

tour.register('google_analytics_add_to_cart', {
    test: true,
    url: '/shop?search=Acoustic Bloc Screens',
},
[
    {
        content: "select Acoustic Bloc Screens",
        trigger: '.oe_product_cart a:contains("Acoustic Bloc Screens")',
    },
    {
        content: "click add to cart button on product page",
        trigger: '#add_to_cart',
    },
    {
        content: 'check add to cart event',
        trigger: 'a:has(.my_cart_quantity:containsExact(1))',
        run: () => {
            const events = websiteSaleTracking.getEvents('add_to_cart');
            if (events.length !== 1) {
                console.error('No add to cart event was generated');
            }
        },
    },
]);

});
