/** @odoo-module **/

import { registry } from "@web/core/registry";
import * as tourUtils from "@website_sale/js/tours/tour_utils";
import { redirect } from "@web/core/utils/urls";

registry.category("web_tour.tours").add('shop_mail', {
    url: '/shop?search=Acoustic Bloc Screens',
    steps: () => [
        ...tourUtils.addToCart({productName: 'Acoustic Bloc Screens', search: false, expectUnloadPage: true}),
        tourUtils.goToCart(),
    {
        content: "check product is in cart, get cart id, go to backend",
        trigger: 'div:has(a>h6:contains("Acoustic Bloc Screens"))',
        run: function () {
            const orderId = document.querySelector(".my_cart_quantity").dataset["orderId"];
            redirect("/odoo/action-sale.action_orders/" + orderId);
        },
        expectUnloadPage: true,
    },
    {
        content: "click confirm",
        trigger: '.btn[name="action_confirm"]',
        run: "click",
    },
    {
        trigger: '.o_statusbar_status .o_arrow_button_current:contains("Sales Order")',
    },
    {
        content: "click send by email",
        trigger: '.btn[name="action_quotation_send"]',
        run: "click",
    },
    {
        isActive: ["body:not(:has(.modal-footer button[name='action_send_mail']))"],
        trigger: ".modal-footer button[name='document_layout_save']",
        content: "let's continue",
        tooltipPosition: "bottom",
        run: "click",
    },
    {
        content: "Open recipients dropdown",
<<<<<<< 4e76444688d1b1bf51bdce42f801a7be28ccfe8c
        trigger: ".modal .o_field_many2many_tags_email[name=partner_ids] input",
        run: 'edit Interior24',
||||||| f0196258ed41f56790db94747192545ae56c78b5
        trigger: '.o_field_many2many_tags_email[name=partner_ids] input',
        run: 'click',
=======
        trigger: '.o_field_many2many_tags_email[name=partner_ids] input',
        run: 'text Azure Interior (Test)',
>>>>>>> 65356cf1511670bb84e97fb51d2e972775b254e8
    },
    {
        content: "Select azure interior",
<<<<<<< 4e76444688d1b1bf51bdce42f801a7be28ccfe8c
        trigger: ".modal .ui-menu-item a:contains(Interior24)",
        run: "click",
    },
    {
        trigger: '.modal .o_badge_text:contains("Azure")',
||||||| f0196258ed41f56790db94747192545ae56c78b5
        trigger: '.ui-menu-item a:contains(olson28)',
        in_modal: false,
=======
        trigger: '.ui-menu-item a:contains(Interior24)',
        in_modal: false,
>>>>>>> 65356cf1511670bb84e97fb51d2e972775b254e8
    },
    {
        content: "click Send email",
<<<<<<< 4e76444688d1b1bf51bdce42f801a7be28ccfe8c
        trigger: '.modal .btn.o_mail_send',
        run: "click",
    },
    {
        trigger: "body:not(:has(.modal))",
||||||| f0196258ed41f56790db94747192545ae56c78b5
        trigger: '.btn[name="action_send_mail"]',
        extra_trigger: '.o_badge_text:contains("Acme")',
=======
        trigger: '.btn[name="action_send_mail"]',
        extra_trigger: '.o_badge_text:contains("Azure")',
>>>>>>> 65356cf1511670bb84e97fb51d2e972775b254e8
    },
    {
        content: "wait mail to be sent, and go see it",
        trigger: '.o-mail-Message-body:contains("Your"):contains("order")',
    },
]});
