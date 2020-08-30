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
            var orderId = $('.my_cart_quantity').data('order-id');
            localStorage.setItem(orderIdKey, orderId);
            window.location.href = "/web/session/logout?redirect=/web/login";
        },
    },
    {
        content: "login as admin and go to the SO (backend)",
        trigger: '.oe_login_form',
        run: function () {
            var orderId = localStorage.getItem(orderIdKey);
            var url = "/web#action=sale.action_orders&view_type=form&id=" + orderId;
            var $loginForm = $('.oe_login_form');
            $loginForm.find('input[name="login"]').val("admin");
            $loginForm.find('input[name="password"]').val("admin");
            $loginForm.find('input[name="redirect"]').val(url);
            $loginForm.submit();
        },
    },
    {
        content: "click action",
        trigger: '.o_dropdown_toggler_btn:contains("Action")',
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
        content: "check the mail is sent, grab the recovery link, and logout",
        trigger: '.o_Message_content a:containsExact("Resume order")',
        run: function () {
            var link = $('.o_Message_content a:containsExact("Resume order")').attr('href');
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
