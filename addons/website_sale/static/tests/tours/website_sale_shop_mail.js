/** @odoo-module **/

import { registry } from "@web/core/registry";
import tourUtils from "@website_sale/js/tours/tour_utils";

registry.category("web_tour.tours").add('shop_mail', {
    test: true,
    url: '/shop?search=Acoustic Bloc Screens',
    steps: () => [
        ...tourUtils.addToCart({productName: 'Acoustic Bloc Screens', search: false}),
        tourUtils.goToCart(),
    {
        content: "check product is in cart, get cart id, go to backend",
        trigger: 'div:has(a>h6:contains("Acoustic Bloc Screens"))',
        run: function () {
            const orderId = document.querySelector(".my_cart_quantity").dataset["orderId"];
            window.location.href = "/web#action=sale.action_orders&view_type=form&id=" + orderId;
        },
    },
    {
        content: "click confirm",
        trigger: '.btn[name="action_confirm"]',
        run: "click",
    },
    {
        content: "click send by email",
        trigger: '.btn[name="action_quotation_send"]',
        extra_trigger: '.o_statusbar_status .o_arrow_button_current:contains("Sales Order")',
        run: "click",
    },
    {
        trigger: ".modal-footer button[name='document_layout_save']",
        extra_trigger: ".modal-footer button[name='document_layout_save']",
        content: "let's continue",
        position: "bottom",
        skip_trigger: ".modal-footer button[name='action_send_mail']",
        run: "click",
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
        run: "click",
    },
    {
        content: "click Send email",
        trigger: '.btn[name="action_send_mail"]',
        extra_trigger: '.o_badge_text:contains("Azure")',
        run: "click",
    },
    {
        content: "wait mail to be sent, and go see it",
        trigger: '.o-mail-Message-body:contains("Your"):contains("order")',
        isCheck: true,
    },
]});
