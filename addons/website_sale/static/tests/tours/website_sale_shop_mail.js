/** @odoo-module **/

import { registry } from "@web/core/registry";
import tourUtils from "@website_sale/js/tours/tour_utils";
import { jsonrpc } from "@web/core/network/rpc_service";

registry.category("web_tour.tours").add('shop_mail', {
    test: true,
    url: '/',
    steps: () => [
    {
        content: "Change the domain of the websites and go to shop",
        trigger: 'body',
        run: function () {
            // We change the domain of the website to test that the email that
            // will be sent uses the correct domain for its links.
            var def1 = jsonrpc("/web/dataset/call_kw/website/write", {
                'model': 'website',
                'method': 'write',
                'args': [[1], {
                    'domain': "my-test-domain.com",
                }],
                kwargs: {},
            });
            // We need to change the domain of all the websites otherwise the
            // website selector will return the website 2 since the domain we
            // set on website 1 doesn't actually match our test server.
            var def2 = jsonrpc("/web/dataset/call_kw/website/write", {
                'model': 'website',
                'method': 'write',
                'args': [[2], {
                    'domain': "https://domain-not-used.fr",
                }],
                kwargs: {},
            });
            Promise.all([def1, def2]).then(function (data) {
                window.location.href = '/shop?search=Acoustic Bloc Screens';
            });
        },
    },
        ...tourUtils.addToCart({productName: 'Acoustic Bloc Screens', search: false}),
        tourUtils.goToCart(),
    {
        content: "check product is in cart, get cart id, go to backend",
        trigger: 'div:has(a>h6:contains("Acoustic Bloc Screens"))',
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
        extra_trigger: '.o_statusbar_status .o_arrow_button_current:contains("Sales Order")',
    },
    {
        content: "Open recipients dropdown",
        trigger: '.o_field_many2many_tags_email[name=partner_ids] input',
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
        trigger: '.o-mail-Message-body:contains("Your"):contains("order")',
        isCheck: true,
    },
]});
