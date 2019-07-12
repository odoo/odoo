odoo.define('website_sale.tour_shop_cart_recovery', function (require) {
'use strict';

var localStorage = require('web.local_storage');
var rpc = require('web.rpc');
var tour = require('web_tour.tour');
require('web.dom_ready');

var orderIdKey = 'website_sale.tour_shop_cart_recovery.orderId';
var recoveryLinkKey = 'website_sale.tour_shop_cart_recovery.recoveryLink';

tour.register('shop_cart_recovery', {
    test: true,
    url: '/shop?search=Acoustic Bloc Screens',
},
[
    {
        content: "select Acoustic Bloc Screens",
        trigger: '.oe_product_cart a:containsExact("Acoustic Bloc Screens")',
    },
    {
        content: "click add to cart",
        trigger: '#product_details #add_to_cart',
    },
    {
        content: "check product is in cart, get cart id, logout, go to login",
        trigger: 'td.td-product_name:contains("Acoustic Bloc Screens")',
        run: function () {
            rpc.query({
                'model': 'website',
                'method': 'sale_get_order',
                'args': [[$('html').data('website-id')]],
            }).then(function (data) {
                window.location.href = "/web/session/logout?redirect=/web/login";
            });
        },
    },
    {
        content: "login as admin and go to the SO (backend)",
        trigger: '.oe_login_form',
        run: function () {
            var url = "/web#action=website_sale.action_orders_ecommerce&view_type=list";
            var $loginForm = $('.oe_login_form');
            $loginForm.find('input[name="login"]').val("admin");
            $loginForm.find('input[name="password"]').val("admin");
            $loginForm.find('input[name="redirect"]').val(url);
            $loginForm.submit();
        },
    },
    {
        content: "remove filter Confirmed Orders",
        trigger: '.o_searchview_input_container .o_searchview_facet:first .o_facet_remove'
    },
    {
        content: "select the order",
        trigger: 'tbody tr:first .o_list_record_selector input[type="checkbox"]',
    },
    {
        content: "click action",
        trigger: '.btn:containsExact("Action")',
    },
    {
        content: "click Send a Cart Recovery Email",
        trigger: 'a:containsExact("Send a Cart Recovery Email")',
    },
    {
        content: "click Send email",
        trigger: '.btn[name="action_send_mail"]',
    },
    {
        content: "click on the order",
        trigger: '.o_data_row:first',
    },
    {
        content: "check the mail is sent, grab the recovery link, and logout",
        trigger: '.o_thread_message_content a:containsExact("Resume order")',
        run: function () {
            var link = $('.o_thread_message_content a:containsExact("Resume order")').attr('href');
            localStorage.setItem(recoveryLinkKey, link);
            window.location.href = "/web/session/logout?redirect=/";
        }
    },
    {
        content: "go to the recovery link",
        trigger: 'a[href="/web/login"]',
        run: function () {
            window.location.href = localStorage.getItem(recoveryLinkKey);
        },
    },
    {
        content: "check the page is working, click on restore",
        extra_trigger: 'p:contains("This is your current cart")',
        trigger: 'p:contains("restore") a:contains("Click here")',
    },
    {
        content: "check product is in restored cart",
        trigger: 'td.td-product_name:contains("Acoustic Bloc Screens")',
        run: function () {},
    },
]);
});
