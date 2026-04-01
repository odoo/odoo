import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { redirect } from "@web/core/utils/urls";
import { post } from "@web/core/network/http_service";
import * as tourUtils from "@website_sale/js/tours/tour_utils";

var orderIdKey = "website_sale.tour_shop_cart_recovery.orderId";
var recoveryLinkKey = "website_sale.tour_shop_cart_recovery.recoveryLink";

registry.category("web_tour.tours").add("website_sale.cart_recovery", {
    steps: () => [
        ...tourUtils.addToCart({ productName: "Acoustic Bloc Screens", expectUnloadPage: true }),
        tourUtils.goToCart(),
        {
            content: "check product is in cart, get cart id, logout, go to login",
            trigger: 'div:has(a>h6:contains("Acoustic Bloc Screens"))',
            run: async function () {
                const orderId = document.querySelector(".my_cart_quantity").dataset["orderId"];
                browser.localStorage.setItem(orderIdKey, orderId);

                const url = await post(
                    "/web/session/logout?redirect=/web/login",
                    { csrf_token: odoo.csrf_token },
                    "url"
                );
                redirect(url);
            },
            expectUnloadPage: true,
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
            content: "edit hidden redirect input to go to sales orders list",
            trigger: '.oe_login_form input[name="redirect"]:hidden',
            run() {
                const url = "/web#action=sale.action_orders&view_type=list";
                this.anchor.value = url;
            },
        },
        {
            content: "login as admin and go to sales orders list",
            trigger: ".oe_login_form .oe_login_buttons button:contains(log in)",
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "remove default Sales Orders filter",
            trigger: 'button.o_facet_remove',
            run: "click",
        },
        {
            content: "check the sales order checkbox",
            trigger: 'td.o_list_record_selector input.form-check-input',
            run: "click",
        },
        {
            content: "click the actions button",
            trigger: 'button.o-dropdown:contains("Actions")',
            run: "click",
        },
        {
            content: "click Send an Email",
            trigger: "span:text(Send an email)",
            run: "click",
        },
        {
            content: "Wait for mail composer to appear",
            trigger: ".o_mail_composer_form",
        },
        {
            content: "select template",
            trigger: ".mail-composer-template-dropdown-btn",
            run: "click",
        },
        {
            content: 'Select the "Ecommerce: Cart Recovery" template from the list.',
            trigger:
                '.mail-composer-template-dropdown.popover .o-dropdown-item:contains("Ecommerce: Cart Recovery")',
            run: "click",
        },
        {
            content: "click Send email",
            trigger: "button.o_mail_send",
            run: "click",
        },
        {
            content: "click on the record to open form view",
            trigger: "tr.o_data_row td[name='name']",
            run: "click",
        },
        {
            content: "check the mail is sent, grab the recovery link, and logout",
            trigger: ".o-mail-Message-body a:text(Resume order)",
            async run({ queryOne }) {
                var link = queryOne('.o-mail-Message-body a:contains("Resume order")').getAttribute(
                    "href"
                );
                browser.localStorage.setItem(recoveryLinkKey, link);

                const url = await post(
                    "/web/session/logout?redirect=/",
                    { csrf_token: odoo.csrf_token },
                    "url"
                );
                redirect(url);
            },
            expectUnloadPage: true,
        },
        {
            content: "go to the recovery link",
            trigger: 'a[href="/web/login"]',
            run: function () {
                const localStorage = browser.localStorage;
                redirect(localStorage.getItem(recoveryLinkKey));
            },
            expectUnloadPage: true,
        },
        {
            trigger: 'p:contains("This is your current cart")',
        },
        {
            content: "check the page is working, click on restore",
            trigger: 'p:contains("restore") a:contains("Click here")',
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "check product is in restored cart",
            trigger: 'div>a>h6:contains("Acoustic Bloc Screens")',
        },
    ],
});
