/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add(
    "website_sale.website_sale_shop_pricelist_tour",
    {
        test: true,
        url: '/shop',
        steps: () => [
            {
                content: "Check pricelist",
                trigger: ".o_pricelist_dropdown .dropdown-toggle:not(:contains('User Pricelist'))",
                run: function() {} // Check
            },
            {
                content: "Go to login page",
                trigger: ".btn:contains('Sign in')",
                run: "click",
            },
            {
                content: "Submit login",
                trigger: '.oe_login_form',
                run: function () {
                    document.querySelector('.oe_login_form input[name="login"]').value = "toto";
                    document.querySelector('.oe_login_form input[name="password"]').value = "long_enough_password";
                    document.querySelector('.oe_login_form input[name="redirect"]').value = "/shop";
                    document.querySelector('.oe_login_form').submit();
                }
            },
            {
                content: "Check pricelist",
                trigger: ".o_pricelist_dropdown .dropdown-toggle:contains('User Pricelist')",
                run: function() {} // Check
            },
        ]
    }
);
