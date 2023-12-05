odoo.define('website_sale.tour_shop_mail', function (require) {
'use strict';

<<<<<<< HEAD
var rpc = require('web.rpc');
const { registry } = require("@web/core/registry");
||||||| parent of 7c08ab9d16ad (temp)
var rpc = require('web.rpc');
var tour = require('web_tour.tour');
=======
var tour = require('web_tour.tour');
>>>>>>> 7c08ab9d16ad (temp)
const tourUtils = require('website_sale.tour_utils');

require('web.dom_ready');

registry.category("web_tour.tours").add('shop_mail', {
    test: true,
<<<<<<< HEAD
    url: '/',
    steps: [
||||||| parent of 7c08ab9d16ad (temp)
    url: '/',
},
[
=======
    url: '/shop?search=Acoustic Bloc Screens',
},
[
>>>>>>> 7c08ab9d16ad (temp)
    {
        content: "select Acoustic Bloc Screens",
        trigger: '.oe_product_cart a:containsExact("Acoustic Bloc Screens")',
    },
    {
        content: "click add to cart",
        trigger: '#product_details #add_to_cart',
    },
        tourUtils.goToCart(),
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
        trigger: '.o_MessageView_content:contains("Your"):contains("order")',
    },
]});
});
