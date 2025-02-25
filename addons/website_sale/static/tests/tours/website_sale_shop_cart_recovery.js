/** @odoo-module **/

import { queryOne } from "@odoo/hoot-dom";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import * as tourUtils from "@website_sale/js/tours/tour_utils";

var orderIdKey = 'website_sale.tour_shop_cart_recovery.orderId';
var recoveryLinkKey = 'website_sale.tour_shop_cart_recovery.recoveryLink';

registry.category("web_tour.tours").add('shop_cart_recovery', {
    url: '/shop',
    steps: () => [
        ...tourUtils.addToCart({productName: "Acoustic Bloc Screens"}),
        tourUtils.goToCart(),
    {
        content: "check product is in cart, get cart id, logout, go to login",
        trigger: 'div:has(a>h6:contains("Acoustic Bloc Screens"))',
        run: function () {
            const orderId = document.querySelector(".my_cart_quantity").dataset["orderId"];
            browser.localStorage.setItem(orderIdKey, orderId);
            window.location.href = "/web/session/logout?redirect=/web/login";
        },
    },
    {
        content: "edit login input",
        trigger: '.oe_login_form input[name="login"]',
        run: "edit admin",
    },
    {
        content: "edit password input",
        trigger: '.oe_login_form input[name="password"]',
        run: "edit admin",
    },
    {
        content: "edit hidden redirect input",
        trigger: '.oe_login_form input[name="redirect"]:hidden',
        run() {
            const orderId = browser.localStorage.getItem(orderIdKey);
            const url = "/odoo/action-sale.action_orders/" + orderId;
            this.anchor.value = url;
        }
    },
    {
        content: "login as admin and go to the SO (backend)",
        trigger: ".oe_login_form .oe_login_buttons button:contains(log in)",
        run: "click",
    },
    {
        content: "click action",
        trigger: '.o_cp_action_menus .dropdown-toggle',
        run: "click",
    },
    {
        content: "click Send an Email",
        trigger: "span:contains(/^Send an email$/)",
        run: "click",
    },
    {
        content: "Wait the modal is opened and form is fullfilled",
        trigger: ".modal main .o_form_view_container [name=subject] input:value(/^S00/)",
    },
    {
        content: "select template",
        trigger: ".mail-composer-template-dropdown-btn",
        run: "click",
    },
    {
        content: 'Select the "Ecommerce: Cart Recovery" template from the list.',
        trigger: '.mail-composer-template-dropdown.popover .o-dropdown-item:contains("Ecommerce: Cart Recovery")',
        run: 'click'
    },
    {
        content: "click Send email",
        trigger: '.btn.o_mail_send',
        run: "click",
    },
    {
        content: "check the mail is sent, grab the recovery link, and logout",
        trigger: ".o-mail-Message-body a:contains(/^Resume order$/)",
        run: function () {
            var link = queryOne('.o-mail-Message-body a:contains("Resume order")').getAttribute('href');
            browser.localStorage.setItem(recoveryLinkKey, link);
            window.location.href = "/web/session/logout?redirect=/";
        }
    },
    {
        content: "go to the recovery link",
        trigger: 'a[href="/web/login"]',
        run: function () {
            const localStorage = browser.localStorage;
            window.location.href = localStorage.getItem(recoveryLinkKey);
        },
    },
    {
        trigger: 'p:contains("This is your current cart")',
    },
    {
        content: "check the page is working, click on restore",
        trigger: 'p:contains("restore") a:contains("Click here")',
        run: "click",
    },
    {
        content: "check product is in restored cart",
        trigger: 'div>a>h6:contains("Acoustic Bloc Screens")',
    },
]});
