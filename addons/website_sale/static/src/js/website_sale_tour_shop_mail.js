odoo.define('website_sale.tour_shop_mail', function (require) {
'use strict';

var base = require('web_editor.base');
var rpc = require('web.rpc');
var tour = require('web_tour.tour');

tour.register('shop_mail', {
    test: true,
    url: '/',
    wait_for: base.ready(),
},
[
    {
        content: "Change the domain of the websites and go to shop",
        trigger: 'body',
        run: function () {
            // We change the domain of the website to test that the email that
            // will be sent uses the correct domain for its links.
            var def1 = rpc.query({
                'model': 'website',
                'method': 'write',
                'args': [[1], {
                    'domain': "my-test-domain.com",
                }],
            });
            // We need to change the domain of all the websites otherwise the
            // website selector will return the website 2 since the domain we
            // set on website 1 doesn't actually match our test server.
            var def2 = rpc.query({
                'model': 'website',
                'method': 'write',
                'args': [[2], {
                    'domain': "https://domain-not-used.fr",
                }],
            });
            $.when(def1, def2).then(function (data) {
                window.location.href = '/shop?search=Acoustic Bloc Screens';
            });
        },
    },
    {
        content: "select Acoustic Bloc Screens",
        trigger: '.oe_product_cart a:containsExact("Acoustic Bloc Screens")',
    },
    {
        content: "click add to cart",
        trigger: '#product_details #add_to_cart',
    },
    {
        content: "check product is in cart, get cart id, go to backend",
        trigger: 'td.td-product_name:contains("Acoustic Bloc Screens")',
        run: function () {
            var orderId = $('.my_cart_quantity').data('order-id');
            window.location.href = "/web#action=sale.action_orders&view_type=form&id=" + orderId;
        },
    },
    {
        content: "click confirm",
        trigger: '.btn[name="action_confirm"]',
    },
    {
        content: "click send by email",
        trigger: '.btn[name="action_quotation_send"]',
        extra_trigger: '.o_statusbar_status .btn-primary:contains("Sales Order")',
    },
    {
        content: "Open recipients dropdown",
        trigger: '.o_field_many2one[name="partner_ids"] .ui-autocomplete-input',
        run: 'click',
    },
    {
        content: "Select azure interior",
        trigger: '.ui-menu-item a:contains(Interior24)',
        in_modal: false,
    },
    {
        content: "click Send email",
        trigger: '.btn[name="action_send_mail"]',
        extra_trigger: '.o_badge_text:contains("Azure")',
    },
    {
        content: "wait mail to be sent, and go see it",
        trigger: '.o_thread_message_content:contains("Here is"):contains("the order")',
        run: function () {
            window.location.href = "/web#action=mail.action_view_mail_mail&view_type=list";
        },
    },
    {
        content: "click on the first email",
        trigger: '.o_data_cell:contains("YourCompany Order")',
    },
    {
        content: "check it's the correct email, and the URL is correct too",
        trigger: 'iframe p:contains("Here is"):contains("the order")',
        extra_trigger: 'iframe a[href^="http://my-test-domain.com"]',
    },
]);
});
